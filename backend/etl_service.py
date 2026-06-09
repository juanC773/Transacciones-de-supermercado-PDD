"""Orquestación ETL: Dataproc Spark (nube) o Python streaming (local/fallback)."""
from __future__ import annotations

import gc

from src.etl.dashboard_data import invalidate_aggregates_cache
from src.etl.load_transactions import AGG_DIR, RAW_PROD, RAW_TRANS, build_aggregates, load_meta
from src.ml.pipeline import ML_DIR, ml_ready
from backend.ml_service import invalidate_ml_cache


def _run_python_etl() -> None:
    from src.etl.load_transactions import _sync_inputs_from_gcs
    from src.storage.gcs import gcs_enabled, sync_products_from_gcs

    invalidate_aggregates_cache()
    invalidate_ml_cache()
    gc.collect()
    if gcs_enabled():
        sync_products_from_gcs(RAW_PROD)
    _sync_inputs_from_gcs()
    build_aggregates(force=True)
    invalidate_aggregates_cache()
    invalidate_ml_cache()


def _sync_results_from_gcs() -> None:
    from src.storage.gcs import gcs_enabled, sync_aggregates_from_gcs

    if gcs_enabled():
        sync_aggregates_from_gcs(AGG_DIR, ML_DIR)
    invalidate_aggregates_cache()
    invalidate_ml_cache()


def run_full_etl() -> dict:
    """
    ETL completo + ML.
    Si DATAPROC_ETL_ENABLED: envía job Spark al cluster y espera hasta timeout.
    Si no: Python streaming en el mismo proceso.
    """
    from src.storage.dataproc import (
        dataproc_etl_enabled,
        get_job_state,
        submit_spark_etl_job,
        wait_for_job,
    )

    if not dataproc_etl_enabled():
        _run_python_etl()
        return {
            "engine": "python",
            "async": False,
            "meta": load_meta(),
            "ml_ready": ml_ready(),
        }

    job_id = submit_spark_etl_job()
    status = wait_for_job(job_id, timeout_sec=270.0)

    if status.get("timed_out"):
        return {
            "engine": "spark-dataproc",
            "async": True,
            "job_id": job_id,
            "state": status.get("state", "RUNNING"),
            "meta": None,
            "ml_ready": ml_ready(),
            "mensaje": "ETL Spark en Dataproc (master + workers). Consulta estado con el job_id.",
        }

    if not status.get("ok"):
        detail = status.get("detail") or status.get("state", "ERROR")
        raise RuntimeError(f"Job Dataproc falló: {detail}")

    _sync_results_from_gcs()
    meta = load_meta()
    return {
        "engine": "spark-dataproc",
        "async": False,
        "job_id": job_id,
        "state": "DONE",
        "meta": meta,
        "ml_ready": ml_ready(),
        "mensaje": "ETL Spark en Dataproc completado; agregados sincronizados desde GCS.",
    }


def etl_job_status(job_id: str) -> dict:
    from src.storage.dataproc import get_job_state

    status = get_job_state(job_id)
    if status.get("ok"):
        _sync_results_from_gcs()
        status["meta"] = load_meta()
        status["ml_ready"] = ml_ready()
    return status
