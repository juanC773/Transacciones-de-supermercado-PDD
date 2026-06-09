# Guía: Spark en GCP + API + Vercel

Arquitectura para el curso **con workers reales en la nube**:

```
CSV (Cloud Storage)
        ↓
Dataproc — Spark cluster (1 master + 2 workers)
        ↓
Parquet + ML (data/processed/ → GCS)
        ↓
Cloud Run — FastAPI (lee agregados)
        ↓
Vercel — Next.js (dashboard)
```

| Capa | Tecnología | ¿Spark? |
|------|------------|---------|
| Batch / ETL | **Dataproc** | **Sí**, PySpark en cluster YARN |
| Serving | Cloud Run + Vercel | No (solo consulta) |

---

## Ingestión (crear tienda, subir CSV, «Procesar»)

Esa funcionalidad está en el código (merge `master` → `deploy`) y funciona **completa en local**:

```powershell
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev
```

En **Cloud Run + Vercel** el dashboard y el ML **sí** funcionan; crear/borrar tienda y reprocesar desde el front **no** (disco efímero del contenedor, timeout, sin cluster Spark). Para la entrega: demo de ingestión en local + dashboard público en Vercel.

---

## Parte 0 — Proyecto GCP

```powershell
gcloud config set project transpdd-tu-iniciales
gcloud services enable storage.googleapis.com dataproc.googleapis.com run.googleapis.com cloudbuild.googleapis.com
```

| Dato | Ejemplo |
|------|---------|
| `PROJECT_ID` | `transpdd-tu-iniciales` |
| `REGION` | `us-central1` |
| `BUCKET` | `transpdd-pdd-datos` |

---

## Parte 1 — Subir CSV al bucket

```powershell
gcloud storage cp DataSet/DataSet/Transactions/102_Tran.csv gs://transpdd-pdd-datos/DataSet/DataSet/Transactions/
# Repetir para 103, 107, 110 y Products/
```

---

## Parte 2 — Dataproc ETL

### 2.1 Crear cluster

**No uses `--max-idle`**: borra el cluster solo tras X minutos sin jobs (por eso desapareció `cluster-pdd-m`). Déjalo corriendo hasta que termines el ETL; luego bórralo tú o déjalo si lo necesitas para la demo.

```powershell
gcloud dataproc clusters create cluster-pdd `
  --region=us-central1 `
  --num-workers=2 `
  --worker-machine-type=e2-standard-4 `
  --master-machine-type=e2-standard-4 `
  --image-version=2.2-debian12
```

### 2.2 Subir código al master (desde PC, rama `deploy`)

En Windows **no uses `~`** en scp; usa ruta absoluta:

```powershell
gcloud compute ssh cluster-pdd-m --zone=us-central1-c --project=transpdd-tu-iniciales --command="mkdir -p /home/Admin/Transacciones-de-supermercado-PDD"

gcloud compute scp --recurse src cluster-pdd-m:/home/Admin/Transacciones-de-supermercado-PDD/ --zone=us-central1-c --project=transpdd-tu-iniciales
```

### 2.3 ETL en el master

```bash
gcloud compute ssh cluster-pdd-m --zone=us-central1-c --project=transpdd-tu-iniciales

cd /home/Admin/Transacciones-de-supermercado-PDD
gcloud storage cp -r gs://transpdd-pdd-datos/DataSet/DataSet DataSet/

pip install -q pandas pyarrow scikit-learn joblib
export ETL_ENGINE=spark
export GCS_BUCKET=transpdd-pdd-datos
python3 -m src.etl.load_transactions
```

En Dataproc Spark lee los CSV **desde GCS** (los workers no ven el disco del master). Los `Products/` locales en el master siguen usándose en el driver.

```bash
# si re-corres el ETL:
rm -f data/processed/aggregates/.done
export ETL_ENGINE=spark
export GCS_BUCKET=transpdd-pdd-datos
python3 -m src.etl.load_transactions

cat data/processed/aggregates/meta.json | grep etl_engine
# debe decir spark-cluster

gcloud storage cp -r data/processed gs://transpdd-pdd-datos/salida/processed
```

### 2.4 Después del ETL

**Importante:** sube `data/processed` a GCS **antes** de cerrar sesión (paso 2.3). Si borras el cluster sin eso, pierdes los Parquet.

Para **dejar el dashboard público hasta el martes** no hace falta mantener Dataproc encendido: basta **Cloud Run + Vercel** (casi gratis). El cluster Dataproc solo se usa para el batch Spark; puedes borrarlo tras el ETL:

```powershell
gcloud dataproc clusters delete cluster-pdd --region=us-central1 --quiet
```

---

## Costos (trial $300 hasta ~martes)

| Recurso | ¿Encendido varios días? | Costo aprox. |
|---------|-------------------------|--------------|
| **Cloud Run** + **Vercel** (dashboard público) | Sí, todo el tiempo | Muy bajo (pocos $ o centavos con poco tráfico) |
| **Cloud Storage** | Sí | Centavos |
| **Dataproc** (12 vCPUs, 3 VMs) | 24/7 varios días | ~$3–6 / hora → ~$70–150 en 4–5 días |
| **Dataproc** solo 2–3 h para ETL | Una vez | ~$10–20 |

Con $300 **alcanza** para dejar **Cloud Run + Vercel** hasta el martes y correr el ETL en Dataproc **una vez**. No necesitas el cluster Dataproc prendido todo el tiempo para que el profesor abra el dashboard.

---

## Parte 3 — Cloud Run (GCS + ingestión en la nube)

Build y deploy (descarga agregados y `Categories.csv` de GCS, **2 GiB RAM**):

```powershell
.\cloud\gcp\deploy-cloud-run.ps1
```

O manual:

```powershell
gcloud builds submit . --config=cloud/gcp/cloudbuild.yaml --project=transpdd-tu-iniciales

gcloud run deploy transpdd-api `
  --image gcr.io/transpdd-tu-iniciales/transpdd-api `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 4Gi --cpu 2 --timeout 300 `
  --set-env-vars "ETL_ENGINE=python,GCS_BUCKET=transpdd-pdd-datos,GCS_DATA_PREFIX=DataSet/DataSet,GCS_OUTPUT_PREFIX=salida/processed"
```

**Permisos:** la cuenta de servicio de Cloud Run necesita `Storage Object Admin` en el bucket `transpdd-pdd-datos`.

Probar: `/api/health` → `aggregates_ready: true`, `gcs_enabled: true`.

**En la nube (Vercel + API):** crear tienda, subir CSV, «Procesar nuevos datos» persisten en GCS y regeneran agregados (ETL Python en Cloud Run). El ETL Spark original sigue en Dataproc (`etl_engine: spark-cluster` hasta el primer reproceso).

---

## Parte 4 — Vercel

1. Import del repo, **Root Directory:** `frontend`.
2. Variable `NEXT_PUBLIC_API_URL` = URL de Cloud Run.
3. Deploy.

CORS: el código permite `https://*.vercel.app` y dominios de producción configurados en `CORS_ORIGINS` (ej. `https://pj-supermercados.lat`).

---

## Checklist entrega

- [ ] ETL en Dataproc con 2 workers
- [ ] `meta.json` con `"etl_engine": "spark-cluster"`
- [ ] `/api/health` OK en Cloud Run
- [ ] Dashboard en Vercel
- [ ] `salida/processed` en GCS (respaldo antes de borrar cluster)
- [ ] Cluster Dataproc apagado tras ETL (opcional; el dashboard no lo necesita)
- [ ] Ingestión en la nube (crear tienda / subir CSV / Procesar) o demo local

---

## Archivos clave

| Archivo | Uso |
|---------|-----|
| [cloud/dataproc/run_etl_on_cluster.sh](../cloud/dataproc/run_etl_on_cluster.sh) | Script ETL en master |
| [cloud/gcp/Dockerfile](../cloud/gcp/Dockerfile) | Imagen Cloud Run |
| [src/etl/store_registry.py](../src/etl/store_registry.py) | Tiendas base + custom |
| [src/etl/spark_load_transactions.py](../src/etl/spark_load_transactions.py) | Detecta `DATAPROC_VERSION` |
