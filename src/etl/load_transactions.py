"""Punto de entrada del ETL: CSV → Parquet en data/processed/aggregates/."""
from __future__ import annotations
import json
import pathlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd

# Rutas: entrada CSV del curso y salida Parquet del ETL.
ROOT = pathlib.Path(__file__).parent.parent.parent
RAW_TRANS = ROOT / "DataSet" / "DataSet" / "Transactions"
RAW_PROD = ROOT / "DataSet" / "DataSet" / "Products"
AGG_DIR = ROOT / "data" / "processed" / "aggregates"
META_FILE = AGG_DIR / "meta.json"
# Tienda 102 trae ids 1-50 (categorías). Las demás traen SKU → ProductCategory.csv.
STORES_WITH_CATEGORY_IDS = {102}
VALID_CATEGORY_MAX = 50

def _load_categories() -> dict[int, str]:
    """Mapa id_categoria -> nombre desde Categories.csv."""
    cat_path = RAW_PROD / "Categories.csv"
    cats = pd.read_csv(
        cat_path, sep="|", header=None, names=["id_categoria", "nombre_categoria"]
    )
    return dict(zip(cats["id_categoria"].astype(int), cats["nombre_categoria"]))


def _load_product_to_categories() -> dict[int, list[int]]:
    """SKU de producto -> una o más categorías (1-50)."""
    cat_path = RAW_PROD / "ProductCategory.csv"
    if not cat_path.exists():
        return {}
    pc = pd.read_csv(
        cat_path, sep="|", header=None, names=["id_producto", "id_categoria"], skiprows=1
    )
    pc["id_producto"] = pd.to_numeric(pc["id_producto"], errors="coerce")
    pc["id_categoria"] = pd.to_numeric(pc["id_categoria"], errors="coerce")
    pc = pc.dropna()
    out: dict[int, list[int]] = defaultdict(list)
    for pid, cid in zip(pc["id_producto"].astype(int), pc["id_categoria"].astype(int)):
        if 1 <= cid <= VALID_CATEGORY_MAX and cid not in out[pid]:
            out[pid].append(cid)
    return dict(out)


def resolve_ticket_categories(
    raw_ids: list[int],
    tienda: int,
    prod_map: dict[int, list[int]] | None = None,
) -> list[int]:
    """Normaliza ítems del ticket a ids de categoría válidos (1-50)."""
    if prod_map is None:
        prod_map = _load_product_to_categories()
    out: list[int] = []
    if tienda in STORES_WITH_CATEGORY_IDS:
        for rid in raw_ids:
            if 1 <= rid <= VALID_CATEGORY_MAX:
                out.append(rid)
        return out
    for rid in raw_ids:
        mapped = prod_map.get(rid)
        if mapped:
            out.append(mapped[0])
        elif 1 <= rid <= VALID_CATEGORY_MAX:
            out.append(rid)
    return out


@dataclass
class _AggState:
    """Acumuladores en memoria durante el recorrido línea a línea del CSV."""
    por_dia: dict = field(default_factory=lambda: defaultdict(lambda: {"unidades": 0, "n_tx": 0}))
    por_semana: dict = field(default_factory=lambda: defaultdict(lambda: {"unidades": 0, "n_tx": 0}))
    por_categoria: dict = field(default_factory=lambda: defaultdict(int))
    por_cliente: dict = field(
        default_factory=lambda: defaultdict(
            lambda: {
                "n_tx": 0,
                "unidades": 0,
                "categorias": set(),
                "fecha_min": None,
                "fecha_max": None,
            }
        )
    )
    # Una fila por ticket: unidades totales del ticket (boxplot por cliente en la API).
    por_tx: list = field(default_factory=list)
    # Canastas: categorías únicas por ticket (recomendador / reglas de asociación).
    canastas: list = field(default_factory=list)
    total_unidades: int = 0
    total_tx: int = 0
    clientes: set = field(default_factory=set)

def _parse_line(
    line: str,
    line_no: int,
    cats: dict[int, str],
    state: _AggState,
    prod_map: dict[int, list[int]],
) -> None:
    """
    Misma lógica que _line_to_rows en Spark, pero sumando en diccionarios
    en vez de crear un DataFrame (rama Python del ETL).
    """
    line = line.strip()
    if not line:
        return
    # Ejemplo: 2013-01-15|102|5001|3 7 7 12
    parts = line.split("|")
    if len(parts) < 4:
        return
    fecha_str, tienda_s, cliente_s, productos_str = parts[0], parts[1], parts[2], parts[3]
    tienda = int(tienda_s)
    cliente = int(cliente_s)
    fecha = pd.Timestamp(fecha_str)
    raw_ids = [int(p) for p in productos_str.split() if p.isdigit()]
    productos = resolve_ticket_categories(raw_ids, tienda, prod_map)
    if not productos:
        return
    conteo = Counter(productos)  # cuenta repeticiones de cada categoría
    unidades_tx = sum(conteo.values())  # tamaño de la canasta
    id_transaccion = f"{tienda}-{fecha_str}-{line_no}"
    state.total_unidades += unidades_tx
    state.total_tx += 1
    state.clientes.add((tienda, cliente))
    key_dia = (fecha, tienda)
    state.por_dia[key_dia]["unidades"] += unidades_tx
    state.por_dia[key_dia]["n_tx"] += 1
    semana = fecha.strftime("%G-W%V")
    key_sem = (semana, tienda)
    state.por_semana[key_sem]["unidades"] += unidades_tx
    state.por_semana[key_sem]["n_tx"] += 1
    for cat_id, qty in conteo.items():
        nombre = cats.get(cat_id, f"Categoría {cat_id}")
        key_cat = (fecha, tienda, cat_id, nombre)
        state.por_categoria[key_cat] += qty
    key_cli = (tienda, cliente)
    cli = state.por_cliente[key_cli]
    cli["n_tx"] += 1
    cli["unidades"] += unidades_tx
    cli["categorias"].update(conteo.keys())
    if cli["fecha_min"] is None or fecha < cli["fecha_min"]:
        cli["fecha_min"] = fecha
    if cli["fecha_max"] is None or fecha > cli["fecha_max"]:
        cli["fecha_max"] = fecha
    state.por_tx.append(
        {
            "fecha": fecha,
            "id_tienda": tienda,
            "id_transaccion": id_transaccion,
            "id_cliente": cliente,
            "cantidad": unidades_tx,
            "mes": fecha.month,
            "dia_semana": fecha.day_name(),
        }
    )
    cats_unicas = " ".join(str(c) for c in sorted(conteo.keys()))
    state.canastas.append(
        {
            "fecha": fecha,
            "id_tienda": tienda,
            "id_transaccion": id_transaccion,
            "id_cliente": cliente,
            "categorias": cats_unicas,
        }
    )

def _process_file(
    csv_path: pathlib.Path,
    cats: dict[int, str],
    state: _AggState,
    prod_map: dict[int, list[int]],
) -> None:
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            _parse_line(line, line_no, cats, state, prod_map)

def _state_to_frames(state: _AggState, cats: dict[int, str]) -> dict[str, pd.DataFrame]:
    """Convierte diccionarios del estado a DataFrames listos para Parquet."""
    por_dia = pd.DataFrame(
        [
            {
                "fecha": k[0],
                "id_tienda": k[1],
                "unidades": v["unidades"],
                "n_transacciones": v["n_tx"],
            }
            for k, v in state.por_dia.items()
        ]
    )
    if not por_dia.empty:
        por_dia["mes"] = por_dia["fecha"].dt.month
        por_dia["dia_semana"] = por_dia["fecha"].dt.day_name()
    por_semana = pd.DataFrame(
        [
            {
                "anio_semana": k[0],
                "id_tienda": k[1],
                "unidades": v["unidades"],
                "n_transacciones": v["n_tx"],
            }
            for k, v in state.por_semana.items()
        ]
    )
    por_categoria = pd.DataFrame(
        [
            {
                "fecha": k[0],
                "id_tienda": k[1],
                "id_categoria": k[2],
                "nombre_categoria": k[3],
                "cantidad": v,
            }
            for k, v in state.por_categoria.items()
        ]
    )
    por_cliente = pd.DataFrame(
        [
            {
                "id_tienda": k[0],
                "id_cliente": k[1],
                "n_transacciones": v["n_tx"],
                "unidades": v["unidades"],
                "n_categorias": len(v["categorias"]),
                "fecha_min": v["fecha_min"],
                "fecha_max": v["fecha_max"],
            }
            for k, v in state.por_cliente.items()
        ]
    )
    if not por_cliente.empty:
        dias = (por_cliente["fecha_max"] - por_cliente["fecha_min"]).dt.days + 1
        por_cliente["dias_activos"] = dias.clip(lower=1)
        por_cliente["frecuencia_semanal"] = por_cliente["n_transacciones"] / (por_cliente["dias_activos"] / 7)
    por_tx = pd.DataFrame(state.por_tx)
    canastas = pd.DataFrame(state.canastas)
    return {
        "por_dia": por_dia,
        "por_semana": por_semana,
        "por_categoria": por_categoria,
        "por_cliente": por_cliente,
        "por_tx": por_tx,
        "canastas": canastas,
    }

def build_aggregates(force: bool = False) -> dict[str, pd.DataFrame]:
    """
    Punto de entrada del ETL.
    Si existe .done y force=False, solo carga Parquet existentes.
    Si ETL_ENGINE=spark, delega en spark_load_transactions; si falla, streaming Python.
    """
    import os
    AGG_DIR.mkdir(parents=True, exist_ok=True)
    marker = AGG_DIR / ".done"
    if marker.exists() and not force:
        return load_aggregates()
    # Rama Spark (local[*]); si falla, continúa con streaming Python abajo.
    engine = os.environ.get("ETL_ENGINE", "spark").lower()
    if engine == "spark":
        try:
            from src.etl.spark_load_transactions import build_aggregates_spark
            return build_aggregates_spark(force=force)
        except Exception as exc:
            print(f"Spark ETL no disponible ({exc}); usando Python streaming.")
    # Rama Python: recorre CSV línea a línea sin cargar todo en RAM.
    cats = _load_categories()
    prod_map = _load_product_to_categories()
    tran_files = sorted(RAW_TRANS.glob("*_Tran.csv"))
    if not tran_files:
        raise FileNotFoundError(f"No se encontraron archivos *_Tran.csv en {RAW_TRANS}")
    state = _AggState()
    for f in tran_files:
        _process_file(f, cats, state, prod_map)
    frames = _state_to_frames(state, cats)
    # Persistencia: un .parquet por tabla agregada + meta.json + marcador .done
    for name, df in frames.items():
        if not df.empty:
            df.to_parquet(AGG_DIR / f"{name}.parquet", index=False)
    meta = {
        "total_unidades": state.total_unidades,
        "total_transacciones": state.total_tx,
        "total_clientes": len(state.clientes),
        "fecha_min": str(min(k[0] for k in state.por_dia)),
        "fecha_max": str(max(k[0] for k in state.por_dia)),
        "tiendas": sorted({k[1] for k in state.por_dia}),
        "generado": datetime.now().isoformat(),
        "etl_engine": "python-streaming",
    }
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    marker.touch()
    _train_ml_safe(frames)
    return frames


def _train_ml_safe(frames: dict[str, pd.DataFrame]) -> None:
    try:
        from src.ml.pipeline import train_ml_models
        train_ml_models(frames)
        print("Modelos ML entrenados (segmentación + recomendador).")
    except Exception as exc:
        print(f"Advertencia: entrenamiento ML omitido ({exc}).")


def load_aggregates() -> dict[str, pd.DataFrame]:
    """Lee todos los .parquet de AGG_DIR; dispara ETL si falta .done."""
    if not (AGG_DIR / ".done").exists():
        return build_aggregates(force=False)
    result = {}
    for path in AGG_DIR.glob("*.parquet"):
        result[path.stem] = pd.read_parquet(path)
    if not META_FILE.exists():
        build_aggregates(force=True)
        return load_aggregates()
    return result

def load_meta() -> dict:
    if not META_FILE.exists():
        build_aggregates(force=False)
    return json.loads(META_FILE.read_text(encoding="utf-8"))

def build_hechos(force: bool = False) -> pd.DataFrame:
    raise MemoryError(
        "hechos.parquet completo no se carga en el dashboard. "
        "Use build_aggregates() o el botón Regenerar datos."
    )

def load_hechos() -> pd.DataFrame:
    raise MemoryError("Use load_aggregates() en lugar de load_hechos().")
if __name__ == "__main__":
    data = build_aggregates(force=True)
    meta = load_meta()
    print("Meta:", meta)
    for k, df in data.items():
        print(f"  {k}: {len(df):,} filas")
