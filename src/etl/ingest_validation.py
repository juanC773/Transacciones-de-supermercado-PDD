"""
Validación de CSV de transacciones antes de ingestión.
Tiendas del dataset base (102, 103, 107, 110) y tiendas registradas por el usuario.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.etl.load_transactions import STORES_WITH_CATEGORY_IDS, VALID_CATEGORY_MAX
from src.etl.store_registry import BASE_STORES, is_registered_store

ALLOWED_STORES = BASE_STORES
MAX_REPORTED_ERRORS = 15
MIN_VALID_LINE_RATIO = 0.95


def _validate_line(line: str, line_no: int, expected_store: int) -> list[str]:
    errs: list[str] = []
    raw = line.strip()
    if not raw:
        return [f"Línea {line_no}: vacía"]
    if raw.lower().startswith("fecha|") or "tienda|cliente" in raw.lower():
        return [f"Línea {line_no}: parece encabezado; el CSV no debe tener header"]

    parts = line.split("|")
    if len(parts) < 4:
        return [f"Línea {line_no}: formato incorrecto (se esperan 4 campos separados por |)"]
    if len(parts) > 4:
        errs.append(f"Línea {line_no}: demasiados campos | ({len(parts)})")

    fecha_s, tienda_s, cliente_s, prod_s = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()

    try:
        datetime.strptime(fecha_s, "%Y-%m-%d")
    except ValueError:
        errs.append(f"Línea {line_no}: fecha inválida '{fecha_s}' (use AAAA-MM-DD)")

    try:
        tienda = int(tienda_s)
        if tienda != expected_store:
            errs.append(f"Línea {line_no}: tienda {tienda} debe ser {expected_store}")
    except ValueError:
        errs.append(f"Línea {line_no}: id de tienda debe ser numérico")

    try:
        cliente = int(cliente_s)
        if cliente <= 0:
            errs.append(f"Línea {line_no}: id_cliente debe ser mayor que 0")
    except ValueError:
        errs.append(f"Línea {line_no}: id_cliente debe ser numérico")

    tokens = prod_s.split()
    if not tokens:
        errs.append(f"Línea {line_no}: falta lista de categorías/productos")
    else:
        for tok in tokens:
            if not tok.isdigit():
                errs.append(f"Línea {line_no}: ítem no numérico '{tok}'")
                break
        if expected_store in STORES_WITH_CATEGORY_IDS:
            for tok in tokens:
                if tok.isdigit():
                    v = int(tok)
                    if v < 1 or v > VALID_CATEGORY_MAX:
                        errs.append(
                            f"Línea {line_no}: categoría {v} fuera de rango 1-{VALID_CATEGORY_MAX}"
                        )
                        break
    return errs


def _non_empty_lines(content: str) -> list[str]:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return [ln for ln in lines if ln.strip()]


def validate_transactions_csv(content: str, required_store: int | None = None) -> dict:
    """
    required_store: si se pasa, el CSV debe ser solo de esa tienda registrada.
    """
    if required_store is not None and not is_registered_store(required_store):
        return {
            "ok": False,
            "errores": [f"Tienda {required_store} no registrada. Créala antes de subir datos."],
            "advertencias": [],
            "lineas_validas": 0,
            "lineas_totales": 0,
            "tienda": required_store,
            "lineas_para_agregar": [],
        }

    non_empty = _non_empty_lines(content)
    if not non_empty:
        return {
            "ok": False,
            "errores": ["El archivo no tiene líneas de datos"],
            "advertencias": [],
            "lineas_validas": 0,
            "lineas_totales": 0,
            "tienda": required_store,
            "lineas_para_agregar": [],
        }

    store = required_store
    if store is None:
        tiendas: set[int] = set()
        for ln in non_empty:
            parts = ln.strip().split("|")
            if len(parts) >= 2:
                try:
                    tiendas.add(int(parts[1].strip()))
                except ValueError:
                    pass
        if not tiendas:
            return {
                "ok": False,
                "errores": ["No se pudo leer id de tienda en la columna 2"],
                "advertencias": [],
                "lineas_validas": 0,
                "lineas_totales": len(non_empty),
                "tienda": None,
                "lineas_para_agregar": [],
            }
        if len(tiendas) > 1:
            ids = ", ".join(str(t) for t in sorted(tiendas))
            return {
                "ok": False,
                "errores": [f"Varias tiendas en un archivo ({ids}). Sube datos por tienda."],
                "advertencias": [],
                "lineas_validas": 0,
                "lineas_totales": len(non_empty),
                "tienda": None,
                "lineas_para_agregar": [],
            }
        store = next(iter(tiendas))
        if not is_registered_store(store):
            return {
                "ok": False,
                "errores": [f"Tienda {store} no registrada. Créala antes de subir datos."],
                "advertencias": [],
                "lineas_validas": 0,
                "lineas_totales": len(non_empty),
                "tienda": store,
                "lineas_para_agregar": [],
            }

    errores: list[str] = []
    lineas_ok: list[str] = []
    for i, line in enumerate(non_empty, start=1):
        line_errs = _validate_line(line, i, store)
        if line_errs:
            errores.extend(line_errs)
        else:
            lineas_ok.append(line.strip())
        if len(errores) >= MAX_REPORTED_ERRORS:
            errores.append("… (más errores omitidos)")
            break

    ratio = len(lineas_ok) / len(non_empty) if non_empty else 0
    if ratio < MIN_VALID_LINE_RATIO:
        errores.insert(
            0,
            f"Solo {len(lineas_ok)}/{len(non_empty)} líneas válidas (mínimo {int(MIN_VALID_LINE_RATIO * 100)}%)",
        )

    ok = len(errores) == 0 and len(lineas_ok) > 0
    return {
        "ok": ok,
        "errores": errores,
        "advertencias": [],
        "lineas_validas": len(lineas_ok),
        "lineas_totales": len(non_empty),
        "tienda": store,
        "lineas_para_agregar": lineas_ok,
        "archivo_destino": f"{store}_Tran.csv",
    }


def append_lines_to_store_file(tienda: int, lineas: list[str], dest_path) -> int:
    """Añade líneas al final del CSV de la tienda. Devuelve cantidad agregada."""
    text = "\n".join(lineas)
    if dest_path.exists() and dest_path.stat().st_size > 0:
        with dest_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write("\n" + text)
    else:
        dest_path.write_text(text + "\n", encoding="utf-8")
    return len(lineas)
