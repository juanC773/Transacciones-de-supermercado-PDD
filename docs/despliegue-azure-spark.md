# Guía completa: Spark en Azure + API + Vercel

Arquitectura objetivo para el curso **con workers reales en la nube**:

```
CSV (Azure Storage)
        ↓
Azure Databricks — Spark cluster (driver + 2+ executors)
        ↓
Parquet + ML (data/processed/)
        ↓
Azure App Service — FastAPI (solo lee agregados)
        ↓
Vercel — Next.js (dashboard)
```

| Capa | Tecnología | ¿Spark? |
|------|------------|---------|
| Batch / ETL | **Databricks** (recomendado) o Synapse Spark | **Sí**, PySpark en cluster |
| Serving | App Service + Vercel | No (solo consulta) |

Guía rápida solo API+front (sin cluster): [despliegue.md](despliegue.md).

---

## Requisitos previos

- Cuenta [Azure](https://azure.microsoft.com/free/students/) (ideal: Azure for Students con crédito).
- Repo en GitHub: `Transacciones-de-supermercado-PDD`.
- Dataset del curso en tu PC (`DataSet/DataSet/`, ver [DataSet/README.md](../DataSet/README.md)).
- ETL probado al menos una vez en local (opcional pero recomendado).

**Tiempo estimado total:** 2–4 h la primera vez.

---

## Parte 1 — Recursos base en Azure

### 1.1 Grupo de recursos

1. [Portal Azure](https://portal.azure.com) → **Grupos de recursos** → **Crear**.
2. Nombre ejemplo: `rg-transacciones-pdd`.
3. Región: la más cercana (ej. `East US`).

### 1.2 Cuenta de almacenamiento (Storage)

1. **Crear recurso** → **Storage account**.
2. Mismo grupo `rg-transacciones-pdd`.
3. Nombre global único: ej. `sttranspdd<tusiniciales>`.
4. Rendimiento: **Standard**, redundancia **LRS**.
5. Crear.

### 1.3 Contenedor y subir CSV

1. En la cuenta → **Contenedores** → **+ Contenedor** → nombre `datos`.
2. Dentro de `datos`, crea la misma estructura que local:

```
datos/
└── DataSet/
    └── DataSet/
        ├── Transactions/
        │   ├── 102_Tran.csv
        │   ├── 103_Tran.csv
        │   ├── 107_Tran.csv
        │   └── 110_Tran.csv
        └── Products/
            ├── Categories.csv
            └── ProductCategory.csv
```

**Portal:** sube carpeta por carpeta, o **Storage Explorer** (app de escritorio).

**PowerShell (alternativa):**

```powershell
$account = "sttranspddTUINICIALES"
az login
az storage blob upload-batch `
  --account-name $account `
  --destination datos `
  --source ".\DataSet\DataSet" `
  --pattern "*"
```

(Ajusta rutas; puede requerir `--auth-mode login`.)

### 1.4 Anotar datos para más tarde

| Dato | Ejemplo |
|------|---------|
| Nombre storage | `sttranspddabc` |
| Contenedor | `datos` |
| Resource group | `rg-transacciones-pdd` |

---

## Parte 2 — Azure Databricks (Spark con workers)

### 2.1 Crear workspace

1. **Crear recurso** → buscar **Azure Databricks**.
2. Plan: **Premium** (trial) o el que permita tu suscripción.
3. Mismo resource group y región que el storage.
4. Crear → **Iniciar workspace** (abre URL `*.azuredatabricks.net`).

### 2.2 Conectar el storage (montaje)

En el workspace → **Catálogo** / notebook → celda:

```python
storage_account = "sttranspddTUINICIALES"
container = "datos"
mount_point = "/mnt/datos"

# Obtén tenant/client secret desde Azure AD App o usa credential passthrough en UI:
# Databricks → Admin → Storage credential / Access connector (recomendado en producción)

configs = {
  "fs.azure.account.auth.type": "OAuth",
  "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
  "fs.azure.account.oauth2.client.id": "<app-id>",
  "fs.azure.account.oauth2.client.secret": "<secret>",
  "fs.azure.account.oauth2.client.endpoint": "https://login.microsoftonline.com/<tenant-id>/oauth2/token",
}

dbutils.fs.mount(
  source=f"abfss://{container}@{storage_account}.dfs.core.windows.net/",
  mount_point=mount_point,
  extra_configs=configs,
)
```

**Atajo para el curso:** en lugar de montaje OAuth, sube el dataset a **DBFS**:

- Workspace → **Data** → **Upload** → sube `DataSet.zip` y descomprime en `/FileStore/DataSet/DataSet/`.

### 2.3 Cluster Spark (workers)

1. **Compute** → **Create cluster**.
2. Sugerido para el dataset del curso:

| Opción | Valor |
|--------|--------|
| Mode | Standard |
| Databricks runtime | **13.3 LTS** o superior (incl. **ML** si quieres sklearn preinstalado) |
| Worker type | `Standard_DS3_v2` (o similar) |
| Min workers | **2** |
| Max workers | **4** |
| Terminate after | 30 min idle (ahorra dinero) |

3. **Create cluster** y espera estado **Running**.

Eso es **Spark distribuido**: 1 driver + N executors (workers).

### 2.4 Traer el código al workspace

**Opción A — Repos (recomendada):**

1. **Repos** → **Add Repo** → URL de GitHub → `Transacciones-de-supermercado-PDD`.
2. Anota la ruta: `/Workspace/Repos/<tu-email>/Transacciones-de-supermercado-PDD`.

**Opción B — Subir ZIP** del proyecto a `/Workspace/Transacciones-de-supermercado-PDD`.

### 2.5 Notebook ETL

1. **File** → **Import** → importa  
   `cloud/databricks/run_etl_notebook.py`  
   del repo (o copia celdas manualmente).
2. Edita `REPO_ROOT` con tu ruta real de Repos.
3. Si usaste mount `/mnt/datos`, descomenta la celda que copia:

```python
REPO_ROOT = "/Workspace/Repos/<usuario>/Transacciones-de-supermercado-PDD"
dbutils.fs.cp("/mnt/datos/DataSet/DataSet", f"file:{REPO_ROOT}/DataSet/DataSet", recurse=True)
```

4. Adjunta el **cluster** al notebook (dropdown arriba a la derecha).
5. **Run all**.

El notebook ejecuta `python -m src.etl.load_transactions` con `ETL_ENGINE=spark`.  
En Databricks el código detecta el runtime y **no** usa `local[*]`; usa el cluster (ver `src/etl/spark_load_transactions.py`).

6. Al terminar, en `meta.json` deberías ver `"etl_engine": "spark-cluster"`.

### 2.6 Copiar salida a Storage (para la API)

Después del ETL, copia `data/processed` al blob:

```python
REPO_ROOT = "/Workspace/Repos/<usuario>/Transacciones-de-supermercado-PDD"
storage_account = "sttranspddTUINICIALES"

dbutils.fs.cp(
  f"file:{REPO_ROOT}/data/processed",
  f"abfss://datos@{storage_account}.dfs.core.windows.net/salida/processed",
  recurse=True,
)
```

O descarga ZIP desde el notebook:

```python
# Empaqueta y descarga por UI de Databricks / FileStore
```

### 2.7 Apagar cluster

**Compute** → cluster → **Terminate** cuando no lo uses (evita cargos).

---

## Parte 3 — Azure App Service (API)

### 3.1 Crear Web App

1. Portal → **App Service** → **Create**.
2. Linux, **Python 3.10** o 3.11.
3. Plan **B1** recomendado (Free es muy lento y sin disco garantizado).
4. Mismo resource group.
5. Deployment: **GitHub** → repo + rama `master`/`main`.

### 3.2 Configuración

**Configuración de la aplicación:**

| Variable | Valor |
|----------|--------|
| `ETL_ENGINE` | `python` (la API no corre Spark; solo sirve Parquet) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
| `CORS_ORIGINS` | URL de Vercel (después del paso 4) |

**Comando de inicio:**

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Build: en el deploy usa `requirements-prod.txt` si cambias el build, o `requirements.txt` completo.

### 3.3 Subir `data/processed`

`data/` no está en Git. Opciones:

**A — Desde tu PC** (si ya corriste ETL local o descargaste de Databricks):

1. Zip `data/processed/`.
2. [Kudu](https://<app>.scm.azurewebsites.net) → `Debug console` → `site/wwwroot`.
3. Crear carpeta `data/processed` y subir contenido (aggregates + ml).

**B — Desde Storage:**

1. En Kudu o script de inicio, descarga `salida/processed` del blob (requiere configurar credenciales en la app; para el curso A es más simple).

Estructura final en el servidor:

```
site/wwwroot/
├── backend/
├── src/
├── data/processed/
│   ├── aggregates/*.parquet, meta.json, .done
│   └── ml/*.json
```

### 3.4 Probar

`https://<tu-app>.azurewebsites.net/api/health`

```json
{
  "status": "ok",
  "aggregates_ready": true,
  "ml_ready": true
}
```

---

## Parte 4 — Vercel (frontend)

1. [vercel.com](https://vercel.com) → Import GitHub repo.
2. **Root Directory:** `frontend`.
3. Variable de entorno:

| Nombre | Valor |
|--------|--------|
| `NEXT_PUBLIC_API_URL` | `https://<tu-app>.azurewebsites.net` |

4. Deploy.
5. Abre la URL de Vercel; si hay error CORS, añade esa URL en `CORS_ORIGINS` en Azure y reinicia la app.

El código ya permite `https://*.vercel.app` por regex en `backend/main.py`.

---

## Parte 5 — Checklist de entrega

- [ ] Cluster Databricks con **≥ 2 workers** usado en el ETL.
- [ ] `meta.json` con `etl_engine`: `spark-cluster`.
- [ ] `/api/health` en Azure OK.
- [ ] Dashboard en Vercel con KPIs y pestañas ML.
- [ ] Informe con diagrama de 3 capas (Storage → Databricks → App Service → Vercel).
- [ ] Cluster **terminado** tras la demo (costos).

---

## Alternativa: Azure Synapse Analytics

Si el curso pide “todo Azure” sin Databricks:

1. Crear **Synapse workspace** en el mismo resource group.
2. **Spark pool** con nodos (ej. Small, 3 nodos).
3. Notebook en Synapse; subir repo o scripts.
4. Variable de entorno `SYNAPSE_SPARK_POOL_USAGE` suele estar activa en el pool; el código la detecta igual que Databricks.
5. Misma salida: Parquet → copiar a Storage → App Service.

Synapse tiene más pasos de red/firewall; para PySpark + curso, **Databricks suele ser más rápido de configurar**.

---

## Qué decir en la presentación (PDD)

> “El procesamiento distribuido ocurre en **Azure Databricks**: PySpark con un cluster de varios workers sobre el dataset en Azure Storage. Materializamos agregados en Parquet y entrenamos segmentación/recomendador en el driver. La **capa serving** (FastAPI en App Service y Next.js en Vercel) solo consume esos artefactos, como en un patrón medallion batch/serving.”

---

## Costos y buenas prácticas

| Recurso | Riesgo |
|---------|--------|
| Databricks cluster prendido | Cobra por DBU + VMs |
| App Service B1 | Costo mensual bajo |
| Vercel hobby | Gratis |
| Storage | Centavos |

**Siempre:** Terminate cluster tras ETL. No dejes Standard_DS3_v2 24/7.

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `No se encontraron *_Tran.csv` | Copiar `DataSet/DataSet` al `REPO_ROOT` en el driver |
| `Java not found` en Databricks | No aplica; usa el runtime del cluster |
| Sigue `spark-local` en meta | No adjuntaste cluster al notebook o no es Databricks |
| OOM en cluster | Sube worker type o `Max workers` |
| ML falla en notebook | `%pip install scikit-learn joblib` |
| `aggregates_ready: false` en Azure | Falta subir `data/processed` a Kudu |
| CORS en Vercel | `CORS_ORIGINS` + reinicio App Service |
| Ingestión “Procesar” timeout en Azure | Demo ingestión en local; en nube solo consulta |

---

## Orden de trabajo (resumen)

1. Storage + subir CSV  
2. Databricks cluster → notebook ETL → `data/processed`  
3. Copiar `data/processed` a App Service (Kudu)  
4. Vercel + `NEXT_PUBLIC_API_URL`  
5. Probar health + dashboard  
6. Apagar cluster  

---

## Archivos del repo relacionados

| Archivo | Uso |
|---------|-----|
| [cloud/databricks/run_etl_notebook.py](../cloud/databricks/run_etl_notebook.py) | Notebook Databricks |
| [src/etl/spark_load_transactions.py](../src/etl/spark_load_transactions.py) | ETL Spark local vs cluster |
| [docs/despliegue.md](despliegue.md) | Solo API + Vercel (sin cluster) |
| [startup.sh](../startup.sh) | Arranque App Service |
| [requirements-prod.txt](../requirements-prod.txt) | API sin PySpark |
