"""Construcción del payload JSON para GET /api/dashboard."""
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from src.etl.dashboard_data import ensure_aggregates, filter_bundle, summary_from_filtered
from src.metrics.executive_summary import (
    actividad_dia_mes_from_agg,
    actividad_por_dia_semana_from_agg,
    categorias_por_volumen_from_agg,
    top_clientes_from_agg,
    top_productos_from_agg,
    ventas_por_dia_from_agg,
    ventas_por_semana_from_agg,
)

FEATURE_LABELS = {
    "n_transacciones": "N° transacciones",
    "unidades": "Unidades totales",
    "n_categorias": "N° categorías",
    "frecuencia_semanal": "Frec. semanal",
}
MESES_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _json_safe(obj: Any) -> Any:
    """NaN/Inf de pandas/numpy rompen json.dumps(allow_nan=False) de Starlette."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return v
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _box_stats(values: pd.Series) -> dict[str, float] | None:
    """Calcula min, Q1, mediana, Q3, max para un boxplot (sin mandar miles de puntos)."""
    if values.empty:
        return None
    sorted_vals = values.sort_values().to_numpy()
    q1 = float(pd.Series(sorted_vals).quantile(0.25))
    median = float(pd.Series(sorted_vals).quantile(0.5))
    q3 = float(pd.Series(sorted_vals).quantile(0.75))
    iqr = q3 - q1
    lo = max(float(sorted_vals[0]), q1 - 1.5 * iqr)
    hi = min(float(sorted_vals[-1]), q3 + 1.5 * iqr)
    return {"min": lo, "q1": q1, "median": median, "q3": q3, "max": hi}


def _boxplot_stats(
    df: pd.DataFrame,
    group_col: str,
    value_col: str = "cantidad",
    top_n: int | None = None,
    name_fn=None,
) -> list[dict[str, Any]]:
    """Agrupa por cliente y devuelve estadísticas de boxplot por cada uno."""
    if df.empty:
        return []
    work = df
    if top_n:
        top_keys = work.groupby(group_col)[value_col].sum().nlargest(top_n).index
        work = work[work[group_col].isin(top_keys)]
    out: list[dict[str, Any]] = []
    for key, grp in work.groupby(group_col, sort=False):
        stats = _box_stats(grp[value_col])
        if stats:
            name = name_fn(key) if name_fn else str(key)
            out.append({"name": name, **stats})
    return out


def _df_records(df: pd.DataFrame, date_cols: list[str] | None = None) -> list[dict[str, Any]]:
    """Convierte DataFrame a lista de dicts (formato que consume Recharts en el frontend)."""
    if df.empty:
        return []
    out = df.copy()
    date_cols = date_cols or []
    for col in date_cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


def build_dashboard_payload(
    tiendas: list[int],
    fecha_min: str,
    fecha_max: str,
) -> dict[str, Any]:
    # --- 1) Cargar Parquet (con caché) y filtrar por UI ---
    agg = ensure_aggregates()
    filt = filter_bundle(agg, tiendas, fecha_min, fecha_max)

    # --- 2) Resumen ejecutivo ---
    kpis = summary_from_filtered(filt)
    top_cat = top_productos_from_agg(filt["por_categoria"], n=10)
    top_cli = top_clientes_from_agg(filt["por_cliente"], n=10)
    por_dia_sem = actividad_por_dia_semana_from_agg(filt["por_dia"])
    if not por_dia_sem.empty:
        dia_map = dict(zip(DIAS_EN, DIAS_ES))
        por_dia_sem = por_dia_sem.copy()
        por_dia_sem["dia"] = por_dia_sem["dia_semana"].map(dia_map)
        por_dia_sem = por_dia_sem.dropna(subset=["dia"])
        por_dia_sem["orden"] = por_dia_sem["dia"].map({d: i for i, d in enumerate(DIAS_ES)})
        por_dia_sem = por_dia_sem.sort_values("orden").drop(columns=["orden", "dia_semana"])
    else:
        por_dia_sem = pd.DataFrame(columns=["dia", "n_transacciones"])
    cats_vol = categorias_por_volumen_from_agg(filt["por_categoria"]).head(10)

    # --- 3) Series temporales ---
    serie_dia = ventas_por_dia_from_agg(filt["por_dia"])
    serie_sem = ventas_por_semana_from_agg(filt["por_semana"])

    # --- 4) Boxplot por cliente (requisito del enunciado) ---
    box_cli_out = _boxplot_stats(
        filt["por_tx"], "id_cliente", top_n=20, name_fn=lambda c: f"C{c}",
    )

    # --- 5) Heatmap correlación (métricas de por_cliente) ---
    feat = filt["por_cliente"]
    cols = [c for c in FEATURE_LABELS if c in feat.columns]
    if feat.empty or len(feat) < 3 or len(cols) < 2:
        heat_corr = {"labels": [], "matrix": []}
    else:
        sub = feat[cols]
        # Con poca data o columnas constantes (p. ej. solo tienda 111) corr() da NaN.
        if sub.std(numeric_only=True).min(skipna=True) == 0:
            heat_corr = {"labels": [], "matrix": []}
        else:
            corr = sub.corr().fillna(0.0)
            labels = [FEATURE_LABELS[c] for c in cols]
            heat_corr = {"labels": labels, "matrix": corr.values.tolist()}

    # --- 6) Heatmap actividad día x mes ---
    pivot_data = actividad_dia_mes_from_agg(filt["por_dia"])
    if pivot_data.empty:
        heat_act = {"dias": [], "meses": [], "values": []}
    else:
        dia_map = dict(zip(DIAS_EN, DIAS_ES))
        pivot_data["dia_semana"] = pivot_data["dia_semana"].map(dia_map)
        pivot = pivot_data.pivot(index="dia_semana", columns="mes", values="n_transacciones").fillna(0)
        pivot.columns = [MESES_ES.get(int(c), str(c)) for c in pivot.columns]
        dias_presentes = [d for d in DIAS_ES if d in pivot.index]
        pivot = pivot.loc[dias_presentes]
        heat_act = {
            "dias": dias_presentes,
            "meses": [str(c) for c in pivot.columns],
            "values": pivot.values.tolist(),
        }

    # --- 7) Un solo JSON para todo el frontend ---
    return _json_safe(
        {
            "kpis": kpis,
            "top_categorias": _df_records(top_cat),
            "top_clientes": _df_records(top_cli),
            "actividad_dia_semana": _df_records(por_dia_sem),
            "categorias_volumen": _df_records(cats_vol),
            "serie_tiempo_dia": _df_records(serie_dia, date_cols=["fecha"]),
            "serie_tiempo_semana": serie_sem.to_dict(orient="records"),
            "boxplot_cliente": box_cli_out,
            "heatmap_correlacion": heat_corr,
            "heatmap_actividad": heat_act,
        }
    )
