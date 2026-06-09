#!/usr/bin/env python3
"""
Punto de entrada para jobs PySpark en Dataproc (enviados desde Cloud Run).
ETL Spark distribuido + ML + subida de salida a GCS.
"""
from __future__ import annotations

import os

os.environ.setdefault("ETL_ENGINE", "spark")
os.environ.setdefault("GCS_DATA_PREFIX", "DataSet/DataSet")
os.environ.setdefault("GCS_OUTPUT_PREFIX", "salida/processed")
os.environ.setdefault("PDD_ETL_FROM_GCS", "1")

from src.etl.load_transactions import AGG_DIR, build_aggregates

if __name__ == "__main__":
    done = AGG_DIR / ".done"
    if done.exists():
        done.unlink()
    build_aggregates(force=True)
    print("Dataproc ETL completado.")
