"""Payloads JSON para segmentación, recomendaciones e ingestión."""
from __future__ import annotations

import pandas as pd

from src.etl.dashboard_data import ensure_aggregates, invalidate_aggregates_cache
from src.ml.pipeline import ml_ready, train_ml_models
from src.ml.recommender import (
    invalidate_recommender_cache,
    load_recommender_meta,
    recommend_for_category,
    recommend_for_client,
)
from src.ml.segmentation import (
    load_segmentation_meta,
    load_segmentation_scatter,
    segmentation_cache_mtime,
)

# Caché en RAM: segmentación es global (no depende de filtros del sidebar).
_seg_payload_cache: dict | None = None
_seg_payload_mtime: float = 0.0


def invalidate_ml_cache() -> None:
    global _seg_payload_cache, _seg_payload_mtime
    _seg_payload_cache = None
    _seg_payload_mtime = 0.0
    invalidate_recommender_cache()


def build_segmentation_payload(
    tiendas: list[int],
    fecha_min: str,
    fecha_max: str,
) -> dict:
    global _seg_payload_cache, _seg_payload_mtime

    if not ml_ready():
        agg = ensure_aggregates()
        if "canastas" not in agg or agg["canastas"].empty:
            raise ValueError("Falta canastas.parquet. Pulsa Regenerar datos (ETL).")
        train_ml_models(agg)
        invalidate_ml_cache()

    mtime = segmentation_cache_mtime()
    if _seg_payload_cache is not None and mtime == _seg_payload_mtime:
        return _seg_payload_cache

    meta = load_segmentation_meta()
    if not meta:
        raise ValueError("Segmentación no entrenada; pulsa Regenerar datos.")

    # Solo JSON pequeños — sin Parquet ni ensure_aggregates (158k filas).
    payload = {
        "meta": meta,
        "scatter": load_segmentation_scatter(),
    }
    _seg_payload_cache = payload
    _seg_payload_mtime = mtime
    return payload


def _filter_canastas(canastas: pd.DataFrame, tiendas: list[int], fecha_min: str, fecha_max: str) -> pd.DataFrame:
    if canastas.empty:
        return canastas
    f_min = pd.Timestamp(fecha_min)
    f_max = pd.Timestamp(fecha_max)
    mask = canastas["id_tienda"].isin(tiendas)
    if "fecha" in canastas.columns:
        mask &= (canastas["fecha"] >= f_min) & (canastas["fecha"] <= f_max)
    return canastas.loc[mask]


def build_recommendations_cliente(
    id_cliente: int,
    tiendas: list[int],
    fecha_min: str,
    fecha_max: str,
) -> dict:
    if not ml_ready():
        train_ml_models(ensure_aggregates())
    agg = ensure_aggregates()
    canastas = agg.get("canastas", pd.DataFrame())
    if canastas.empty:
        cli = canastas
    else:
        cli = canastas.loc[canastas["id_cliente"] == id_cliente]
        cli = _filter_canastas(cli, tiendas, fecha_min, fecha_max)
    recs = recommend_for_client(id_cliente, cli)
    return {
        "id_cliente": id_cliente,
        "recomendaciones": recs,
        "nota": "Categorías sugeridas (dataset sin SKU de producto).",
    }


def build_recommendations_categoria(id_categoria: int) -> dict:
    if not ml_ready():
        train_ml_models(ensure_aggregates())
    recs = recommend_for_category(id_categoria)
    return {
        "id_categoria": id_categoria,
        "recomendaciones": recs,
        "meta": load_recommender_meta(),
    }
