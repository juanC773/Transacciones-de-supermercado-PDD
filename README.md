# Análisis de transacciones de supermercado

Sistema de analítica sobre transacciones de retail: ETL con PySpark, API REST y dashboard web. Incluye resumen ejecutivo, visualizaciones, segmentación K-Means, recomendador por reglas de asociación e ingestión de nuevos datos por tienda.

**Curso:** Procesamiento distribuido de datos  
**Periodo de datos:** enero–junio 2013 · Tiendas 102, 103, 107, 110

---

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/instalacion.md](docs/instalacion.md) | Requisitos, instalación, ETL y puesta en marcha |
| [docs/manual-usuario.md](docs/manual-usuario.md) | Uso del dashboard, filtros e ingestión de datos |
| [docs/arquitectura.md](docs/arquitectura.md) | Arquitectura, flujo de datos y mapa del código |
| [DataSet/README.md](DataSet/README.md) | Estructura y formato de los CSV de entrada |

---

## Inicio rápido

```powershell
# 1. Entorno Python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Dataset (ver DataSet/README.md)
# Colocar CSV en DataSet/DataSet/Transactions/ y Products/

# 3. ETL (genera data/processed/)
python -m src.etl.load_transactions

# 4. API
uvicorn backend.main:app --reload --port 8000

# 5. Frontend (otra terminal)
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Abrir http://localhost:3000

---

## Arquitectura

```
CSV  →  ETL (Spark local / Python)  →  Parquet (data/processed/)
                                              ↓
                                        FastAPI (backend/)
                                              ↓
                                        Next.js (frontend/)
```

El ETL se ejecuta en batch. El dashboard consulta agregados ya materializados y aplica filtros de tienda y fecha en la API.

---

## Estructura del repositorio

```
├── backend/              # API FastAPI
├── frontend/             # Dashboard Next.js
├── src/
│   ├── etl/              # Carga, validación e ingestión
│   ├── metrics/          # KPIs y agregaciones para la API
│   └── ml/               # Segmentación y recomendador
├── DataSet/              # CSV de entrada (no versionados)
├── data/processed/       # Salida ETL y modelos (generado localmente)
└── docs/                 # Documentación técnica
```

---

## API (referencia)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Estado del servicio y agregados |
| GET | `/api/meta` | Metadatos del dataset procesado |
| GET | `/api/dashboard` | KPIs y gráficos (filtros: tiendas, fechas) |
| GET | `/api/segmentacion` | Clusters K-Means y scatter PCA |
| GET | `/api/recomendaciones/cliente` | Sugerencias por cliente |
| GET | `/api/recomendaciones/categoria` | Sugerencias por categoría |
| POST | `/api/ingest/tienda/{id}` | Agregar líneas al CSV de una tienda |
| POST | `/api/ingest/procesar` | Reprocesar ETL y modelos ML |
| POST | `/api/etl/regenerar` | Regenerar agregados desde cero |

---

## Notas sobre el dataset

- Las métricas usan **unidades vendidas** (cantidad de ítems). No hay precios ni montos.
- La tienda **102** registra categorías (1–50). Las demás usan SKU mapeados vía `ProductCategory.csv`.
- El “top de productos” en el dashboard corresponde a **categorías**, acorde a la granularidad disponible.

---

## Variables de entorno

| Variable | Valor | Uso |
|----------|-------|-----|
| `ETL_ENGINE` | `spark` (default) o `python` | Motor del ETL |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL de la API en el frontend |
