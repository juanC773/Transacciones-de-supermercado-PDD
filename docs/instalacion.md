# Instalación y despliegue local

## Requisitos

| Componente | Versión |
|------------|---------|
| Python | 3.10 o superior |
| Node.js | 18 o superior |
| Java | 11+ (solo si se usa ETL con Spark) |

Además, el dataset del curso debe estar en `DataSet/DataSet/` (ver [DataSet/README.md](../DataSet/README.md)).

---

## 1. Configuración del entorno Python

Desde la raíz del proyecto:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

En Linux/macOS: `source venv/bin/activate`.

---

## 2. Configuración del frontend

```powershell
cd frontend
npm install
copy .env.local.example .env.local    # Windows
# cp .env.local.example .env.local    # Linux/macOS
cd ..
```

El archivo `frontend/.env.local` debe contener:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 3. Procesamiento inicial (ETL)

Con el entorno virtual activo:

```powershell
python -m src.etl.load_transactions
```

Este comando:

1. Lee los CSV de `DataSet/DataSet/Transactions/`
2. Genera agregados Parquet en `data/processed/aggregates/`
3. Entrena modelos de segmentación y recomendaciones en `data/processed/ml/`
4. Crea el marcador `data/processed/aggregates/.done`

Duración estimada: 1–5 minutos según hardware y motor ETL.

### Motor ETL

Por defecto se usa Spark en modo local (`local[*]`). Si Java o Spark no están disponibles:

```powershell
$env:ETL_ENGINE="python"
python -m src.etl.load_transactions
```

---

## 4. Ejecución de los servicios

**Terminal 1 — API:**

```powershell
venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

Verificar: http://localhost:8000/api/health  
Debe responder `"aggregates_ready": true`.

**Terminal 2 — Dashboard:**

```powershell
cd frontend
npm run dev
```

Abrir http://localhost:3000

---

## 5. Regeneración de datos

| Acción | Comando / ubicación |
|--------|---------------------|
| Regenerar agregados | Botón «Regenerar datos (Spark)» o `POST /api/etl/regenerar` |
| Tras agregar CSV por tienda | Botón «Procesar nuevos datos» o `POST /api/ingest/procesar` |
| Línea de comandos | `python -m src.etl.load_transactions` (con `force=True` vía API) |

Para volver al dataset original: restaurar los CSV en `DataSet/DataSet/Transactions/`, eliminar `data/processed/` y ejecutar el ETL de nuevo.

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Dashboard sin datos | API apagada o ETL no ejecutado | Verificar `:8000/api/health` y correr ETL |
| Gráficos vacíos | Ninguna tienda seleccionada | Activar al menos una tienda en el sidebar |
| Error CORS / fetch | Falta `.env.local` | Crear `frontend/.env.local` con la URL de la API |
| Spark falla al iniciar | Java no instalado | Usar `ETL_ENGINE=python` |
| Error al subir CSV | Falta `python-multipart` | `pip install python-multipart` |
| Segmentación vacía | Modelos ML no generados | Regenerar ETL completo |

---

## Estructura de salida del ETL

```
data/processed/
├── aggregates/
│   ├── por_dia.parquet
│   ├── por_semana.parquet
│   ├── por_categoria.parquet
│   ├── por_cliente.parquet
│   ├── por_tx.parquet
│   ├── canastas.parquet
│   ├── meta.json
│   └── .done
└── ml/
    ├── segmentacion_meta.json
    ├── segmentacion_scatter.json
    ├── reglas_asociacion.json
    └── ml_summary.json
```

Estos directorios están excluidos del control de versiones; deben generarse en cada máquina donde se evalúe el proyecto.
