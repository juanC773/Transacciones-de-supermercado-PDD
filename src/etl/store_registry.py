"""Tiendas del dataset base y tiendas creadas por el usuario."""
from __future__ import annotations

import json
from pathlib import Path

from src.etl.load_transactions import RAW_TRANS
from src.storage.gcs import (
    blob_exists,
    delete_blob,
    download_blob,
    ensure_local_file,
    gcs_enabled,
    read_text,
    stores_key,
    touch_blob,
    tran_key,
    upload_file,
    write_text,
)

BASE_STORES = frozenset({102, 103, 107, 110})
BASE_STORE_NAMES: dict[int, str] = {
    102: "Tienda 102",
    103: "Tienda 103",
    107: "Tienda 107",
    110: "Tienda 110",
}
REGISTRY_FILE = RAW_TRANS.parent / "stores.json"
MAX_NAME_LEN = 80


def _load_custom() -> dict[str, dict[str, str]]:
    if gcs_enabled():
        raw = read_text(stores_key())
        if raw:
            data = json.loads(raw)
            custom = data.get("custom", {})
            return custom if isinstance(custom, dict) else {}
    if not REGISTRY_FILE.exists():
        return {}
    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    custom = data.get("custom", {})
    return custom if isinstance(custom, dict) else {}


def _save_custom(custom: dict[str, dict[str, str]]) -> None:
    payload = json.dumps({"custom": custom}, indent=2, ensure_ascii=False)
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(payload, encoding="utf-8")
    write_text(stores_key(), payload)


def store_csv_path(store_id: int) -> Path:
    return RAW_TRANS / f"{store_id}_Tran.csv"


def store_csv_exists(store_id: int) -> bool:
    path = store_csv_path(store_id)
    if path.exists():
        return True
    if gcs_enabled():
        return ensure_local_file(tran_key(store_id), path) or blob_exists(tran_key(store_id))
    return False


def ensure_store_csv_local(store_id: int) -> bool:
    """Descarga el CSV de GCS si hace falta. Devuelve si existe."""
    path = store_csv_path(store_id)
    if path.exists():
        return True
    if gcs_enabled():
        return download_blob(tran_key(store_id), path)
    return path.exists()


def _prune_custom_registry() -> dict[str, dict[str, str]]:
    """Elimina del registro las tiendas custom cuyo CSV ya no existe."""
    custom = _load_custom()
    stale = [sid for sid in custom if not store_csv_exists(int(sid))]
    if not stale:
        return custom
    for sid in stale:
        del custom[sid]
    if custom:
        _save_custom(custom)
    elif REGISTRY_FILE.exists():
        REGISTRY_FILE.unlink()
        if gcs_enabled():
            delete_blob(stores_key())
    return custom


def list_stores() -> list[dict]:
    custom = _prune_custom_registry()
    stores: list[dict] = []
    for sid in sorted(BASE_STORES):
        stores.append({"id": sid, "nombre": BASE_STORE_NAMES[sid], "es_base": True})
    for sid_s, info in sorted(custom.items(), key=lambda item: int(item[0])):
        stores.append(
            {
                "id": int(sid_s),
                "nombre": info.get("nombre", f"Tienda {sid_s}"),
                "es_base": False,
            }
        )
    return stores


def is_registered_store(store_id: int) -> bool:
    if store_id in BASE_STORES:
        return True
    return str(store_id) in _prune_custom_registry()


def create_store(store_id: int, nombre: str) -> dict:
    nombre = nombre.strip()
    errors: list[str] = []
    if store_id <= 0:
        errors.append("El id de tienda debe ser un entero positivo")
    if store_id in BASE_STORES:
        errors.append(f"La tienda {store_id} ya forma parte del dataset del curso")
    custom = _load_custom()
    csv_exists = store_csv_exists(store_id)
    in_registry = str(store_id) in custom

    if csv_exists and in_registry:
        errors.append(f"La tienda {store_id} ya está registrada")
    elif csv_exists and store_id not in BASE_STORES:
        errors.append(f"Ya existe el archivo {store_id}_Tran.csv")
    elif in_registry and not csv_exists:
        custom[str(store_id)] = {"nombre": nombre}
        _save_custom(custom)
        RAW_TRANS.mkdir(parents=True, exist_ok=True)
        store_csv_path(store_id).touch()
        touch_blob(tran_key(store_id))
        return {"id": store_id, "nombre": nombre, "es_base": False}
    if not nombre:
        errors.append("El nombre no puede estar vacío")
    if len(nombre) > MAX_NAME_LEN:
        errors.append(f"El nombre es demasiado largo (máx. {MAX_NAME_LEN} caracteres)")

    if errors:
        raise ValueError("; ".join(errors))

    custom[str(store_id)] = {"nombre": nombre}
    _save_custom(custom)
    RAW_TRANS.mkdir(parents=True, exist_ok=True)
    store_csv_path(store_id).touch()
    touch_blob(tran_key(store_id))
    return {"id": store_id, "nombre": nombre, "es_base": False}


def delete_store(store_id: int) -> dict:
    if store_id in BASE_STORES:
        raise ValueError("No se pueden eliminar las tiendas del dataset del curso (102, 103, 107, 110)")
    custom = _load_custom()
    key = str(store_id)
    if key not in custom:
        raise ValueError(f"La tienda {store_id} no está registrada o ya fue eliminada")

    del custom[key]
    if custom:
        _save_custom(custom)
    elif REGISTRY_FILE.exists():
        REGISTRY_FILE.unlink()
        if gcs_enabled():
            delete_blob(stores_key())

    csv = store_csv_path(store_id)
    if csv.exists():
        csv.unlink()
    if gcs_enabled():
        delete_blob(tran_key(store_id))

    return {"id": store_id, "eliminada": True}


def upload_store_csv_append(store_id: int, lineas: list[str]) -> int:
    """Añade líneas al CSV de la tienda (local + GCS)."""
    text = "\n".join(lineas)
    dest = store_csv_path(store_id)
    RAW_TRANS.mkdir(parents=True, exist_ok=True)
    ensure_store_csv_local(store_id)
    if dest.exists() and dest.stat().st_size > 0:
        with dest.open("a", encoding="utf-8", newline="\n") as f:
            f.write("\n" + text)
    else:
        dest.write_text(text + "\n", encoding="utf-8")
    if gcs_enabled():
        upload_file(dest, tran_key(store_id))
    return len(lineas)
