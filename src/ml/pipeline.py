"""
Entrena modelos ML tras el ETL (segmentación + recomendador).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.etl.load_transactions import load_aggregates
from src.ml.recommender import train_recommender
from src.ml.segmentation import train_segmentation

ML_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "ml"


def train_ml_models(agg: dict[str, pd.DataFrame] | None = None) -> dict:
    """Entrena K-Means y reglas; la segmentación se guarda aunque falle el recomendador."""
    if agg is None:
        agg = load_aggregates()

    por_cliente = agg.get("por_cliente", pd.DataFrame())
    canastas = agg.get("canastas", pd.DataFrame())

    if por_cliente.empty:
        raise ValueError("Falta por_cliente.parquet; ejecuta el ETL primero.")
    if canastas.empty:
        raise ValueError("Falta canastas.parquet; regenera el ETL (versión actual).")

    seg_meta = train_segmentation(por_cliente)

    rec_meta = None
    rec_error = None
    try:
        rec_meta = train_recommender(canastas)
    except Exception as exc:
        rec_error = str(exc)
        print(f"Advertencia recomendador: {exc}")

    summary = {
        "entrenado": datetime.now().isoformat(),
        "segmentacion": seg_meta,
        "recomendador": rec_meta,
        "recomendador_error": rec_error,
    }
    (ML_DIR / "ml_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def ml_ready() -> bool:
    return (ML_DIR / "segmentacion_meta.json").exists()


def recommender_ready() -> bool:
    return (ML_DIR / "reglas_asociacion.json").exists()
