"""Tiendas del dataset base y tiendas creadas por el usuario."""
from __future__ import annotations

import json
from pathlib import Path

from src.etl.load_transactions import RAW_TRANS

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
    if not REGISTRY_FILE.exists():
        return {}
    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    custom = data.get("custom", {})
    return custom if isinstance(custom, dict) else {}


def _save_custom(custom: dict[str, dict[str, str]]) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(
        json.dumps({"custom": custom}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def store_csv_path(store_id: int) -> Path:
    return RAW_TRANS / f"{store_id}_Tran.csv"


def _prune_custom_registry() -> dict[str, dict[str, str]]:
    """Quita del registro tiendas custom sin CSV (p. ej. borrado manual del archivo)."""
    custom = _load_custom()
    stale = [sid for sid in custom if not store_csv_path(int(sid)).exists()]
    if not stale:
        return custom
    for sid in stale:
        del custom[sid]
    if custom:
        _save_custom(custom)
    elif REGISTRY_FILE.exists():
        REGISTRY_FILE.unlink()
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
    csv_exists = store_csv_path(store_id).exists()
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

    csv = store_csv_path(store_id)
    if csv.exists():
        csv.unlink()

    return {"id": store_id, "eliminada": True}
