"""Envío y seguimiento de jobs ETL Spark en Dataproc desde Cloud Run."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DRIVER_LOCAL = ROOT / "cloud" / "dataproc" / "run_spark_etl.py"
GCS_JOBS_PREFIX = "dataproc/jobs"


def dataproc_etl_enabled() -> bool:
    return os.environ.get("DATAPROC_ETL_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _project_id() -> str:
    pid = os.environ.get("GCP_PROJECT", "").strip()
    if pid:
        return pid
    import google.auth

    _, project = google.auth.default()
    if not project:
        raise RuntimeError("GCP_PROJECT no configurado y sin proyecto por defecto en ADC")
    return project


def _region() -> str:
    return os.environ.get("DATAPROC_REGION", "us-central1").strip()


def _cluster() -> str:
    name = os.environ.get("DATAPROC_CLUSTER", "cluster-pdd").strip()
    if not name:
        raise RuntimeError("DATAPROC_CLUSTER no configurado")
    return name


def _bucket() -> str:
    return os.environ.get("GCS_BUCKET", "transpdd-pdd-datos").strip()


def _job_client():
    from google.cloud import dataproc_v1

    return dataproc_v1.JobControllerClient(
        client_options={"api_endpoint": f"{_region()}-dataproc.googleapis.com:443"}
    )


def _upload_etl_bundle() -> tuple[str, str]:
    """Sube driver + zip de src/ a GCS. Devuelve URIs gs://."""
    from src.storage.gcs import upload_file

    bucket = _bucket()
    tmp = Path(tempfile.mkdtemp(prefix="pdd_dataproc_"))
    try:
        zip_path = tmp / "pdd_src.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            src_dir = ROOT / "src"
            for path in src_dir.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    zf.write(path, path.relative_to(ROOT).as_posix())

        driver_copy = tmp / "run_spark_etl.py"
        shutil.copy2(DRIVER_LOCAL, driver_copy)

        driver_key = f"{GCS_JOBS_PREFIX}/run_spark_etl.py"
        zip_key = f"{GCS_JOBS_PREFIX}/pdd_src.zip"
        upload_file(driver_copy, driver_key)
        upload_file(zip_path, zip_key)
        return (f"gs://{bucket}/{driver_key}", f"gs://{bucket}/{zip_key}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def submit_spark_etl_job() -> str:
    """Lanza job PySpark en el cluster Dataproc. Devuelve job_id."""
    from google.cloud import dataproc_v1

    driver_uri, src_zip_uri = _upload_etl_bundle()
    bucket = _bucket()
    props = {
        "spark.yarn.appMasterEnv.ETL_ENGINE": "spark",
        "spark.yarn.appMasterEnv.GCS_BUCKET": bucket,
        "spark.yarn.appMasterEnv.GCS_DATA_PREFIX": os.environ.get("GCS_DATA_PREFIX", "DataSet/DataSet"),
        "spark.yarn.appMasterEnv.GCS_OUTPUT_PREFIX": os.environ.get("GCS_OUTPUT_PREFIX", "salida/processed"),
        "spark.yarn.appMasterEnv.PDD_ETL_FROM_GCS": "1",
        "spark.executorEnv.GCS_BUCKET": bucket,
        "spark.executorEnv.PDD_ETL_FROM_GCS": "1",
    }

    job = dataproc_v1.Job(
        placement=dataproc_v1.JobPlacement(cluster_name=_cluster()),
        pyspark_job=dataproc_v1.PySparkJob(
            main_python_file_uri=driver_uri,
            python_file_uris=[src_zip_uri],
            properties=props,
        ),
        labels={"job_type": "pdd_etl"},
    )
    result = _job_client().submit_job(
        request={"project_id": _project_id(), "region": _region(), "job": job}
    )
    job_id = result.reference.job_id
    if not job_id:
        raise RuntimeError("Dataproc no devolvió job_id")
    return job_id


def get_job_state(job_id: str) -> dict:
    """Estado del job Dataproc."""
    from google.cloud import dataproc_v1

    job = _job_client().get_job(
        request={
            "project_id": _project_id(),
            "region": _region(),
            "job_id": job_id,
        }
    )
    state = job.status.state.name if job.status and job.status.state else "UNKNOWN"
    detail = ""
    if job.status and job.status.details:
        detail = job.status.details
    elif job.status and job.status.state_message:
        detail = job.status.state_message
    return {
        "job_id": job_id,
        "state": state,
        "detail": detail,
        "done": state in ("DONE", "ERROR", "CANCELLED"),
        "ok": state == "DONE",
    }


def wait_for_job(job_id: str, timeout_sec: float = 270.0, poll_sec: float = 5.0) -> dict:
    """Espera a que termine el job (para endpoints síncronos con límite de timeout)."""
    deadline = time.monotonic() + timeout_sec
    last: dict = {}
    while time.monotonic() < deadline:
        last = get_job_state(job_id)
        if last["done"]:
            return last
        time.sleep(poll_sec)
    last["timed_out"] = True
    return last
