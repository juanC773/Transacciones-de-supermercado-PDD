# Despliegue: Azure (API) + Vercel (dashboard)

> **Spark con workers en la nube (Databricks + Storage + API + Vercel):**  
> ver la guía completa **[despliegue-azure-spark.md](despliegue-azure-spark.md)**.

Orden recomendado (solo serving): **datos en tu PC → API en Azure → front en Vercel**.

---

## Fase 0 — En tu computador (antes de la nube)

1. Dataset del curso en `DataSet/DataSet/` (ver `DataSet/README.md`).
2. ETL local:

```powershell
venv\Scripts\activate
$env:ETL_ENGINE="python"
python -m src.etl.load_transactions
```

3. Comprobar: `http://localhost:8000/api/health` → `aggregates_ready: true` y `ml_ready: true`.

Sin esto, la API en Azure arranca vacía.

---

## Fase 1 — Backend en Azure App Service

### 1.1 Crear recurso

1. [Portal Azure](https://portal.azure.com) → **Crear recurso** → **App Service**.
2. **Runtime:** Linux, **Python 3.10** o 3.11.
3. Plan: **Free F1** o **Basic B1** (B1 recomendado si vas a correr ETL en el servidor).
4. Publicación: **Código** o **GitHub** (repo `Transacciones-de-supermercado-PDD`).

### 1.2 Configuración de la app

En **Configuración** → **Configuración de la aplicación** → Variables:

| Nombre | Valor |
|--------|--------|
| `ETL_ENGINE` | `python` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
| `ENABLE_ORYX_BUILD` | `true` |
| `CORS_ORIGINS` | *(vacío al inicio; tras Vercel: `https://tu-app.vercel.app`)* |

En **Configuración** → **Configuración general** → **Comando de inicio**:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

(Azure inyecta `PORT`; si falla, usa `startup.sh` con permisos de ejecución.)

### 1.3 Dependencias en Azure

En la raíz del deploy, Oryx usa `requirements.txt` por defecto. Para deploy más liviano (sin Spark):

- Renombrar temporalmente o configurar el build para instalar `requirements-prod.txt`, **o**
- Dejar `requirements.txt` y `ETL_ENGINE=python` (instala PySpark pero no lo usa).

### 1.4 Subir datos procesados

`data/` y `DataSet/**` no están en Git. Opciones:

**A — Recomendada para entrega:** ZIP por Kudu

1. En tu PC, con ETL ya corrido, crea un zip con:
   - `data/processed/` (carpeta completa)
2. App Service → **Herramientas avanzadas (Kudu)** → `https://<app>.scm.azurewebsites.net`
3. **Debug console** → `site/wwwroot` → arrastrar/descomprimir `data/processed` ahí.

**B — ETL en Azure:** sube también el dataset por Kudu a `DataSet/DataSet/` y ejecuta en **SSH/Consola**:

```bash
cd /home/site/wwwroot
export ETL_ENGINE=python
python -m src.etl.load_transactions
```

(Puede tardar varios minutos; plan Free es lento.)

### 1.5 Probar API

`https://<tu-app>.azurewebsites.net/api/health`

Debe devolver `"aggregates_ready": true`.

---

## Fase 2 — Frontend en Vercel

1. [vercel.com](https://vercel.com) → **Import** del mismo repo GitHub.
2. **Root Directory:** `frontend`
3. **Environment Variable:**

| Nombre | Valor |
|--------|--------|
| `NEXT_PUBLIC_API_URL` | `https://<tu-app>.azurewebsites.net` |

4. Deploy.

5. Copia la URL de Vercel (ej. `https://transacciones-xxx.vercel.app`) y en Azure añade en `CORS_ORIGINS` esa URL (sin barra final). Reinicia la App Service.

El regex por defecto ya permite subdominios `*.vercel.app`; `CORS_ORIGINS` sirve si usas dominio custom.

---

## Fase 3 — Checklist final

- [ ] `/api/health` en Azure OK
- [ ] Dashboard en Vercel carga KPIs (sin error de red en consola)
- [ ] Pestañas Segmentación y Recomendaciones con datos
- [ ] Demo ingestión en la nube: opcional; si el POST tarda >2 min, hacer ingestión en local

---

## Solución de problemas

| Síntoma | Qué hacer |
|---------|-----------|
| CORS / blocked by CORS | Añadir URL de Vercel en `CORS_ORIGINS` y reiniciar Azure |
| `aggregates_ready: false` | Subir `data/processed` o correr ETL en el servidor |
| Build muy lento o falla | Usar `requirements-prod.txt` en el build |
| Procesar datos timeout | Aumentar timeout en plan superior o procesar en local |
