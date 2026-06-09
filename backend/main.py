"""
API HTTP: dashboard, ETL, ingestión de CSV, segmentación K-Means y recomendaciones.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, Field


def _cors_origins() -> list[str]:
    """Orígenes permitidos: desarrollo local, producción y CORS_ORIGINS."""
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://pj-supermercados.lat",
        "https://www.pj-supermercados.lat",
    ]
    extra = os.environ.get("CORS_ORIGINS", "")
    for origin in extra.split(","):
        origin = origin.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.dashboard_service import build_dashboard_payload
from backend.ml_service import (
    build_recommendations_categoria,
    build_recommendations_cliente,
    build_segmentation_payload,
    invalidate_ml_cache,
)
from src.etl.dashboard_data import aggregates_mtime, invalidate_aggregates_cache
from src.etl.load_transactions import AGG_DIR, RAW_TRANS, build_aggregates, load_meta
from src.ml.pipeline import ml_ready, train_ml_models

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    from src.etl.load_transactions import RAW_PROD
    from src.ml.pipeline import ML_DIR
    from src.storage.gcs import gcs_enabled, sync_aggregates_from_gcs, sync_products_from_gcs

    if gcs_enabled():
        sync_aggregates_from_gcs(AGG_DIR, ML_DIR)
        sync_products_from_gcs(RAW_PROD)
    yield


app = FastAPI(title="Transacciones Supermercado API", version="1.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=os.environ.get("CORS_ORIGIN_REGEX") or r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateStoreBody(BaseModel):
    id_tienda: int = Field(..., gt=0, description="Id numérico de la tienda (columna 2 del CSV)")
    nombre: str = Field(..., min_length=1, max_length=80, description="Nombre visible en el dashboard")


def _parse_tiendas(tiendas: str) -> list[int]:
    try:
        return [int(t.strip()) for t in tiendas.split(",") if t.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tiendas inválidas") from exc


def _run_full_etl() -> None:
    """Reconstruye agregados Parquet + ML desde los CSV actuales (GCS o local)."""
    import gc

    from src.etl.load_transactions import RAW_PROD, _sync_inputs_from_gcs
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


@app.get("/api/health")
def health():
    from src.storage.gcs import gcs_enabled

    return {
        "status": "ok",
        "aggregates_ready": aggregates_mtime() > 0,
        "ml_ready": ml_ready(),
        "gcs_enabled": gcs_enabled(),
    }


@app.get("/api/meta")
def meta():
    if aggregates_mtime() == 0:
        build_aggregates(force=False)
        invalidate_aggregates_cache()
    return load_meta()


@app.post("/api/etl/regenerar")
def regenerar_etl():
    try:
        _run_full_etl()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ETL falló: {exc}") from exc
    return {"ok": True, "meta": load_meta(), "ml_ready": ml_ready()}


@app.post("/api/ml/entrenar")
def entrenar_ml():
    invalidate_aggregates_cache()
    summary = train_ml_models()
    return {"ok": True, "summary": summary}


@app.get("/api/dashboard")
def dashboard(
    tiendas: str = Query("102,103,107,110"),
    fecha_min: str = Query("2013-01-01"),
    fecha_max: str = Query("2013-06-30"),
):
    if aggregates_mtime() == 0:
        build_aggregates(force=False)
        invalidate_aggregates_cache()
    tiendas_list = _parse_tiendas(tiendas)
    if not tiendas_list:
        raise HTTPException(status_code=400, detail="Selecciona al menos una tienda")
    return build_dashboard_payload(tiendas_list, fecha_min, fecha_max)


@app.get("/api/segmentacion")
def segmentacion(
    tiendas: str = Query("102,103,107,110"),
    fecha_min: str = Query("2013-01-01"),
    fecha_max: str = Query("2013-06-30"),
):
    tiendas_list = _parse_tiendas(tiendas)
    try:
        return build_segmentation_payload(tiendas_list, fecha_min, fecha_max)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/recomendaciones/cliente")
def recomendaciones_cliente(
    id_cliente: int = Query(..., description="ID del cliente"),
    tiendas: str = Query("102,103,107,110"),
    fecha_min: str = Query("2013-01-01"),
    fecha_max: str = Query("2013-06-30"),
):
    tiendas_list = _parse_tiendas(tiendas)
    return build_recommendations_cliente(id_cliente, tiendas_list, fecha_min, fecha_max)


@app.get("/api/recomendaciones/categoria")
def recomendaciones_categoria(
    id_categoria: int = Query(..., description="ID de categoría (1-50)"),
):
    return build_recommendations_categoria(id_categoria)


@app.get("/api/tiendas")
def list_tiendas():
    from src.etl.store_registry import list_stores

    return {"tiendas": list_stores()}


@app.post("/api/tiendas")
def crear_tienda(body: CreateStoreBody):
    from src.etl.store_registry import create_store

    try:
        tienda = create_store(body.id_tienda, body.nombre.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "tienda": tienda}


@app.delete("/api/tiendas/{id_tienda}")
def eliminar_tienda(id_tienda: int):
    from src.etl.store_registry import delete_store

    try:
        result = delete_store(id_tienda)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        _run_full_etl()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ETL tras borrado falló: {exc}") from exc
    return {
        "ok": True,
        **result,
        "meta": load_meta(),
        "ml_ready": ml_ready(),
        "mensaje": f"Tienda {id_tienda} eliminada y agregados actualizados sin sus datos.",
    }


@app.post("/api/ingest/tienda/{id_tienda}")
async def ingest_agregar_tienda(id_tienda: int, file: UploadFile = File(...)):
    """Añade líneas validadas al CSV de una tienda registrada."""
    from src.etl.ingest_validation import append_lines_to_store_file, validate_transactions_csv
    from src.etl.store_registry import ensure_store_csv_local, is_registered_store, store_csv_exists, store_csv_path

    if not is_registered_store(id_tienda):
        raise HTTPException(status_code=400, detail=f"Tienda {id_tienda} no registrada")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")
    content = await file.read()
    if len(content) < 5:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="El archivo debe estar en UTF-8")

    report = validate_transactions_csv(text, required_store=id_tienda)
    if not report["ok"]:
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "El CSV no pasó la validación",
                "errores": report["errores"],
                "lineas_validas": report["lineas_validas"],
                "lineas_totales": report["lineas_totales"],
            },
        )

    RAW_TRANS.mkdir(parents=True, exist_ok=True)
    dest = store_csv_path(id_tienda)
    if not store_csv_exists(id_tienda):
        raise HTTPException(
            status_code=404,
            detail=f"No existe {dest.name}. Crea la tienda o restaura el dataset del curso.",
        )
    ensure_store_csv_local(id_tienda)

    n = append_lines_to_store_file(id_tienda, report["lineas_para_agregar"])
    return {
        "ok": True,
        "tienda": id_tienda,
        "archivo": dest.name,
        "lineas_agregadas": n,
        "mensaje": f"{n} líneas agregadas a tienda {id_tienda}. Pulsa «Procesar nuevos datos».",
    }


@app.post("/api/ingest/procesar")
def ingest_procesar():
    """ETL completo + entrenamiento ML tras incorporar nuevos CSV."""
    try:
        _run_full_etl()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ETL falló: {exc}") from exc
    return {
        "ok": True,
        "meta": load_meta(),
        "ml_ready": ml_ready(),
        "aggregates_dir": str(AGG_DIR),
    }
