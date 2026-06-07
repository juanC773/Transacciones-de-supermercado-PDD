"""Carga y filtrado de agregados Parquet para la API."""
from __future__ import annotations
from typing import Any
import pandas as pd
from src.etl.load_transactions import AGG_DIR, build_aggregates, load_aggregates

# Caché global: evita releer disco en cada clic del usuario en el dashboard
_agg_cache: dict[str, pd.DataFrame] | None = None
_agg_cache_mtime: float = 0.0


def _local_mtime() -> float:
    marker = AGG_DIR / ".done"
    return marker.stat().st_mtime if marker.exists() else 0.0


def aggregates_mtime() -> float:
    """Hora de modificación de .done; si cambia, hay que recargar caché."""
    from src.storage.gcs import aggregates_gcs_mtime, gcs_enabled

    local = _local_mtime()
    if gcs_enabled():
        return max(local, aggregates_gcs_mtime())
    return local


def invalidate_aggregates_cache() -> None:
    """Llamar después de POST /api/etl/regenerar para forzar nueva lectura."""
    global _agg_cache, _agg_cache_mtime
    _agg_cache = None
    _agg_cache_mtime = 0.0


def ensure_aggregates() -> dict[str, pd.DataFrame]:
    """
    Devuelve dict con por_dia, por_categoria, por_cliente, por_tx, etc.
    Primera petición: lee Parquet. Siguientes: reutiliza RAM si .done no cambió.
    """
    global _agg_cache, _agg_cache_mtime
    from src.ml.pipeline import ML_DIR
    from src.storage.gcs import aggregates_gcs_mtime, gcs_enabled, sync_aggregates_from_gcs

    if gcs_enabled() and aggregates_gcs_mtime() > _local_mtime():
        sync_aggregates_from_gcs(AGG_DIR, ML_DIR)
        invalidate_aggregates_cache()

    # Si nunca corrió el ETL, lo ejecuta ahora
    if not (AGG_DIR / ".done").exists():
        invalidate_aggregates_cache()
        _agg_cache = build_aggregates(force=True)
        _agg_cache_mtime = aggregates_mtime()
        return _agg_cache

    mtime = aggregates_mtime()
    if _agg_cache is not None and mtime == _agg_cache_mtime:
        return _agg_cache  # hit de caché

    _agg_cache = load_aggregates()
    _agg_cache_mtime = mtime
    return _agg_cache


def filter_bundle(
    agg: dict[str, pd.DataFrame],
    tiendas: list[int],
    fecha_min,
    fecha_max,
) -> dict[str, pd.DataFrame]:
    """
    Aplica los filtros del sidebar (tiendas 102,103... y rango de fechas).
    Devuelve las mismas tablas pero recortadas.
    """
    f_min = pd.Timestamp(fecha_min)
    f_max = pd.Timestamp(fecha_max)

    def _f(df: pd.DataFrame, need_fecha: bool = True) -> pd.DataFrame:
        if df.empty:
            return df
        mask = df["id_tienda"].isin(tiendas)
        if need_fecha and "fecha" in df.columns:
            mask &= (df["fecha"] >= f_min) & (df["fecha"] <= f_max)
        return df.loc[mask]

    # Cliente: incluir si su actividad solapa el rango de fechas elegido
    por_cliente = agg["por_cliente"]
    if not por_cliente.empty:
        mask_cli = por_cliente["id_tienda"].isin(tiendas)
        mask_cli &= (por_cliente["fecha_max"] >= f_min) & (por_cliente["fecha_min"] <= f_max)
        por_cliente_f = por_cliente.loc[mask_cli]
    else:
        por_cliente_f = por_cliente

    por_dia_f = _f(agg["por_dia"])

    # Semanas: alinear con los días que quedaron tras filtrar fechas
    por_semana_f = agg["por_semana"]
    if not por_semana_f.empty and not por_dia_f.empty:
        semanas = por_dia_f["fecha"].dt.strftime("%G-W%V").unique()
        por_semana_f = por_semana_f.loc[
            por_semana_f["id_tienda"].isin(tiendas) & por_semana_f["anio_semana"].isin(semanas)
        ]
    elif not por_semana_f.empty:
        por_semana_f = por_semana_f.loc[por_semana_f["id_tienda"].isin(tiendas)]

    canastas_f = _f(agg.get("canastas", pd.DataFrame()))
    return {
        "por_dia": por_dia_f,
        "por_semana": por_semana_f,
        "por_categoria": _f(agg["por_categoria"]),
        "por_cliente": por_cliente_f,
        "por_tx": _f(agg["por_tx"]),
        "canastas": canastas_f,
    }


def summary_from_filtered(filt: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """KPIs del tab Resumen: unidades, transacciones, clientes."""
    por_dia = filt["por_dia"]
    por_tx = filt["por_tx"]
    por_cliente = filt["por_cliente"]

    n_tx = int(por_dia["n_tx"].sum()) if not por_dia.empty and "n_tx" in por_dia.columns else 0
    if n_tx == 0 and "n_transacciones" in por_dia.columns and not por_dia.empty:
        n_tx = int(por_dia["n_transacciones"].sum())
    if n_tx == 0 and not por_tx.empty:
        n_tx = int(por_tx["id_transaccion"].nunique())

    return {
        "total_ventas": int(por_dia["unidades"].sum()) if not por_dia.empty else 0,
        "total_transacciones": n_tx,
        "total_clientes": int(por_cliente["id_cliente"].nunique()) if not por_cliente.empty else 0,
    }
