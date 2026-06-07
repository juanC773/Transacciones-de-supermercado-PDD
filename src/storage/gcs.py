"""Lectura/escritura en GCS con caché local bajo /app."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

GCS_DATA_PREFIX = os.environ.get("GCS_DATA_PREFIX", "DataSet/DataSet").strip("/")
GCS_OUTPUT_PREFIX = os.environ.get("GCS_OUTPUT_PREFIX", "salida/processed").strip("/")


def gcs_enabled() -> bool:
    return bool(os.environ.get("GCS_BUCKET", "").strip())


def _bucket_name() -> str:
    name = os.environ.get("GCS_BUCKET", "").strip()
    if not name:
        raise RuntimeError("GCS_BUCKET no configurado")
    return name


@lru_cache(maxsize=1)
def _client():
    from google.cloud import storage

    return storage.Client()


def _blob_key(rel: str) -> str:
    return rel.replace("\\", "/").lstrip("/")


def _bucket():
    return _client().bucket(_bucket_name())


def blob_exists(key: str) -> bool:
    if not gcs_enabled():
        return False
    return _bucket().blob(_blob_key(key)).exists()


def read_text(key: str) -> str | None:
    if not gcs_enabled():
        return None
    blob = _bucket().blob(_blob_key(key))
    if not blob.exists():
        return None
    return blob.download_as_text(encoding="utf-8")


def write_text(key: str, content: str) -> None:
    if not gcs_enabled():
        return
    _bucket().blob(_blob_key(key)).upload_from_string(content, content_type="text/plain; charset=utf-8")


def touch_blob(key: str) -> None:
    write_text(key, "")


def delete_blob(key: str) -> None:
    if not gcs_enabled():
        return
    blob = _bucket().blob(_blob_key(key))
    if blob.exists():
        blob.delete()


def append_text(key: str, extra: str) -> None:
    if not gcs_enabled():
        return
    current = read_text(key) or ""
    if current and not current.endswith("\n"):
        current += "\n"
    write_text(key, current + extra)


def download_blob(key: str, local: Path) -> bool:
    if not gcs_enabled():
        return local.exists()
    blob = _bucket().blob(_blob_key(key))
    if not blob.exists():
        return False
    local.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local))
    return True


def upload_file(local: Path, key: str) -> None:
    if not gcs_enabled() or not local.exists():
        return
    _bucket().blob(_blob_key(key)).upload_from_filename(str(local))


def ensure_local_file(key: str, local: Path) -> bool:
    if local.exists():
        return True
    return download_blob(key, local)


def list_blobs(prefix: str) -> list[str]:
    if not gcs_enabled():
        return []
    p = _blob_key(prefix).rstrip("/") + "/"
    return [b.name for b in _client().list_blobs(_bucket_name(), prefix=p)]


def mtime(key: str) -> float:
    if not gcs_enabled():
        return 0.0
    blob = _bucket().blob(_blob_key(key))
    if not blob.exists():
        return 0.0
    blob.reload()
    updated = blob.updated
    if updated is None:
        return 0.0
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return updated.timestamp()


def stores_key() -> str:
    return f"{GCS_DATA_PREFIX}/stores.json"


def tran_key(store_id: int) -> str:
    return f"{GCS_DATA_PREFIX}/Transactions/{store_id}_Tran.csv"


def sync_transactions_from_gcs(raw_trans: Path) -> int:
    """Descarga *_Tran.csv de GCS al directorio local. Devuelve cantidad."""
    if not gcs_enabled():
        return len(list(raw_trans.glob("*_Tran.csv")))
    raw_trans.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in list_blobs(f"{GCS_DATA_PREFIX}/Transactions"):
        if not name.endswith("_Tran.csv"):
            continue
        local = raw_trans / Path(name).name
        if download_blob(name, local):
            n += 1
    return n


def sync_products_from_gcs(raw_prod: Path) -> None:
    if not gcs_enabled():
        return
    raw_prod.mkdir(parents=True, exist_ok=True)
    for fname in ("Categories.csv", "ProductCategory.csv"):
        key = f"{GCS_DATA_PREFIX}/Products/{fname}"
        download_blob(key, raw_prod / fname)


def _gcs_agg_prefix() -> str:
    return f"{GCS_OUTPUT_PREFIX}/aggregates"


def _gcs_ml_prefix() -> str:
    return f"{GCS_OUTPUT_PREFIX}/ml"


def _agg_prefixes() -> list[str]:
    base = _gcs_agg_prefix()
    legacy = f"{GCS_OUTPUT_PREFIX}/processed/aggregates"
    return [base] if base == legacy else [base, legacy]


def _ml_prefixes() -> list[str]:
    base = _gcs_ml_prefix()
    legacy = f"{GCS_OUTPUT_PREFIX}/processed/ml"
    return [base] if base == legacy else [base, legacy]


def sync_aggregates_from_gcs(agg_dir: Path, ml_dir: Path) -> None:
    if not gcs_enabled():
        return
    agg_dir.mkdir(parents=True, exist_ok=True)
    ml_dir.mkdir(parents=True, exist_ok=True)
    for prefix in _agg_prefixes():
        for name in list_blobs(prefix):
            if name.endswith("/"):
                continue
            download_blob(name, agg_dir / Path(name).name)
    for prefix in _ml_prefixes():
        for name in list_blobs(prefix):
            if name.endswith("/"):
                continue
            download_blob(name, ml_dir / Path(name).name)


def sync_aggregates_to_gcs(agg_dir: Path, ml_dir: Path) -> None:
    if not gcs_enabled():
        return
    if agg_dir.exists():
        for path in agg_dir.iterdir():
            if path.is_file():
                upload_file(path, f"{_gcs_agg_prefix()}/{path.name}")
    if ml_dir.exists():
        for path in ml_dir.iterdir():
            if path.is_file():
                upload_file(path, f"{_gcs_ml_prefix()}/{path.name}")


def aggregates_gcs_mtime() -> float:
    stamps = [mtime(f"{p}/.done") for p in _agg_prefixes()]
    stamps += [mtime(f"{p}/meta.json") for p in _agg_prefixes()]
    return max(stamps) if stamps else 0.0
