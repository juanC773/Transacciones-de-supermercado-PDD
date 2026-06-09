# Diagrama de despliegue en la nube

Arquitectura del proyecto **Transacciones-de-supermercado-PDD** en producción (GCP + Vercel).

---

## ⭐ Diagrama único — toda la arquitectura

**Archivo:** `docs/diagrama-deploy-nube.md` (este archivo, sección de abajo).

**Cómo verlo / exportarlo a PNG para la presentación:**

| Opción | Dónde |
|--------|--------|
| **A — Cursor / VS Code** | Abre este archivo → `Ctrl+Shift+V` (vista previa Markdown) |
| **B — Web (mejor para PNG)** | Copia el bloque `mermaid` de abajo → [mermaid.live](https://mermaid.live) → **Actions → Export PNG/SVG** |
| **C — Desde la guía** | `docs/despliegue-gcp-spark.md` tiene el enlace a este doc |

```mermaid
flowchart TB
    classDef user fill:#DBEAFE,stroke:#2563EB,stroke-width:2px
    classDef vercel fill:#18181B,stroke:#71717A,color:#FAFAFA
    classDef gcp fill:#DCFCE7,stroke:#16A34A,stroke-width:2px
    classDef storage fill:#FFEDD5,stroke:#EA580C,stroke-width:2px
    classDef batch fill:#F3E8FF,stroke:#9333EA,stroke-width:2px
    classDef dev fill:#E0E7FF,stroke:#4F46E5,stroke-width:2px

    U(["👤 Usuario / Profesor"]):::user

    subgraph VERCEL["VERCEL — Dashboard"]
        FE["Next.js<br/>frontend/<br/>transacciones-de-supermercado-pdd.vercel.app"]:::vercel
    end

    subgraph GCP["GOOGLE CLOUD — proyecto transpdd-tu-iniciales · us-central1"]
        subgraph RUN["CLOUD RUN — API en producción"]
            API["transpdd-api<br/>FastAPI · Python 3.11<br/>4 GiB · timeout 300s"]:::gcp
        end

        subgraph GCS["CLOUD STORAGE — gs://transpdd-pdd-datos"]
            direction TB
            CSV["📄 DataSet/DataSet/Transactions/<br/>102_Tran.csv … 111_Tran.csv"]:::storage
            PROD["📄 Products/ · stores.json"]:::storage
            AGG["📊 salida/processed/aggregates/<br/>Parquet + meta.json"]:::storage
            ML["🤖 salida/processed/ml/<br/>K-Means · reglas"]:::storage
        end

        subgraph DP["DATAPROC — ETL Spark (curso PDD)"]
            SPARK["cluster-pdd<br/>1 master + 2 workers<br/>PySpark · YARN"]:::batch
        end

        subgraph DEPLOY["CLOUD BUILD + GCR — deploy del código"]
            BUILD["cloudbuild.yaml + Dockerfile<br/>gcr.io/.../transpdd-api"]:::gcp
        end
    end

    subgraph PC["TU PC — desarrollo"]
        CODE["backend/ · src/ · .py"]:::dev
        SCRIPT[".\\cloud\\gcp\\deploy-cloud-run.ps1"]:::dev
        GIT["git push → rama deploy"]:::dev
    end

    U -->|"① Abre el dashboard"| FE
    FE -->|"② REST API<br/>dashboard · ingest · tiendas"| API
    API <-->|"③ Lee/escribe datos"| CSV
    API <-->|"③"| PROD
    API <-->|"③ Sync + ETL Python"| AGG
    API <-->|"③"| ML

    SPARK -->|"ETL batch Spark"| AGG
    SPARK -->|"ETL batch"| ML
    SPARK -.->|"Lee CSV"| CSV

    CODE --> SCRIPT
    SCRIPT -->|"gcloud builds submit"| BUILD
    SCRIPT -->|"gcloud run deploy"| API
    BUILD --> API

    GIT -->|"Auto deploy front"| FE

    U -.->|"Subir CSV · Procesar · Eliminar tienda"| FE
```

### Leyenda rápida

| Flecha | Significado |
|--------|-------------|
| ① Usuario → Vercel | Entra al dashboard público |
| ② Vercel → Cloud Run | El front llama a la API (`NEXT_PUBLIC_API_URL`) |
| ③ Cloud Run ↔ GCS | CSV, Parquet y ML; fuente de verdad en el bucket |
| Dataproc → GCS | ETL **Spark** del curso (batch, cluster con workers) |
| Tu PC → Cloud Build → Cloud Run | Cómo subes cambios de `.py` (`deploy-cloud-run.ps1`) |
| git push → Vercel | Cómo subes cambios del **frontend** (rama `deploy`) |

---

## 1. Vista general — ¿quién habla con quién?

```mermaid
flowchart TB
    classDef user fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef vercel fill:#000000,stroke:#333,color:#fff
    classDef gcp fill:#E8F5E9,stroke:#34A853,color:#1B5E20
    classDef storage fill:#FFF3E0,stroke:#FB8C00,color:#E65100
    classDef batch fill:#F3E5F5,stroke:#8E24AA,color:#4A148C

    U(["👤 Usuario / Profesor<br/>Navegador web"]):::user
    V(["▲ Vercel<br/>Next.js — frontend/"]):::vercel
    CR(["☁ Cloud Run<br/>transpdd-api<br/>FastAPI · 4 GiB · us-central1"]):::gcp
    GCS[("🪣 Cloud Storage<br/>gs://transpdd-pdd-datos")]:::storage
    DP(["⚡ Dataproc<br/>cluster-pdd<br/>1 master + 2 workers<br/><i>solo ETL batch Spark</i>"]):::batch

    U -->|"HTTPS"| V
    V -->|"NEXT_PUBLIC_API_URL<br/>/api/dashboard · /api/ingest · …"| CR
    CR <-->|"lee/escribe CSV, Parquet, ML"| GCS
    DP -->|"ETL PySpark → sube salida"| GCS
    DP -.->|"lee Transactions/*.csv"| GCS

    class U,V,CR,GCS,DP user
```

| Componente | URL / recurso | Rol |
|------------|---------------|-----|
| **Vercel** | `transacciones-de-supermercado-pdd.vercel.app` | Dashboard, filtros, gráficos |
| **Cloud Run** | `transpdd-api-….us-central1.run.app` | API REST + ETL Python en la nube |
| **Cloud Storage** | `gs://transpdd-pdd-datos` | Fuente de verdad (CSV, Parquet, tiendas) |
| **Dataproc** | `cluster-pdd` (apagable tras ETL) | ETL distribuido con **Spark** (curso PDD) |

---

## 2. Dentro del bucket GCS — qué guarda cada carpeta

```mermaid
flowchart LR
    subgraph BUCKET["gs://transpdd-pdd-datos"]
        direction TB
        T["DataSet/DataSet/Transactions/<br/>102_Tran.csv … 111_Tran.csv"]
        P["DataSet/DataSet/Products/<br/>Categories.csv · ProductCategory.csv"]
        S["DataSet/DataSet/stores.json<br/>tiendas custom"]
        A["salida/processed/aggregates/<br/>por_dia · por_tx · meta.json …"]
        M["salida/processed/ml/<br/>segmentación · reglas"]
    end

    CR2[Cloud Run API]
    DP2[Dataproc Spark]

    CR2 <-->|upload / sync| T
    CR2 <-->|sync| P
    CR2 <-->|CRUD tiendas| S
    CR2 <-->|sync / ETL Python| A
    CR2 <-->|sync ML| M
    DP2 -->|ETL batch| A
    DP2 -->|ETL batch| M
    DP2 -->|lee| T
```

---

## 3. Flujo en tiempo de ejecución — dashboard e ingestión

```mermaid
sequenceDiagram
    actor U as Usuario
    participant V as Vercel (Next.js)
    participant A as Cloud Run (FastAPI)
    participant G as GCS

    Note over U,G: Consultar dashboard
    U->>V: Marca tiendas / fechas
    V->>A: GET /api/dashboard?tiendas=…
    A->>G: sync Parquet (si hay cambios)
    A->>A: Filtra agregados en RAM
    A-->>V: JSON (KPIs, gráficos)
    V-->>U: Actualiza pantalla

    Note over U,G: Ingestión en la nube
    U->>V: Sube CSV a tienda 111
    V->>A: POST /api/ingest/tienda/111
    A->>G: append 111_Tran.csv
    A-->>V: ok — «Pulsa Procesar»

    U->>V: Procesar nuevos datos
    V->>A: POST /api/ingest/procesar (~1–2 min)
    A->>G: descarga todos los CSV
    A->>A: ETL Python streaming
    A->>G: sube Parquet + ML
    A-->>V: meta actualizada
    V-->>U: Dashboard refrescado

    Note over U,G: Eliminar tienda (hard delete)
    U->>V: Eliminar tienda custom
    V->>A: DELETE /api/tiendas/111 (~1–2 min)
    A->>G: borra CSV + stores.json
    A->>A: ETL sin esa tienda
    A->>G: Parquet sin datos de 111
```

---

## 4. Flujo de deploy — ¿cómo llega tu código `.py` a la nube?

**La nube no ve los archivos de tu PC solos.** Hay que empaquetar y desplegar.

```mermaid
flowchart TB
    classDef local fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    classDef build fill:#FFF8E1,stroke:#F9A825,color:#F57F17
    classDef run fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20

    subgraph PC["💻 Tu PC"]
        PY["backend/ · src/<br/>archivos .py"]:::local
        DCK["cloud/gcp/Dockerfile"]:::local
        PS1["deploy-cloud-run.ps1"]:::local
    end

    subgraph CICD["Google Cloud Build"]
        CB["cloudbuild.yaml"]:::build
        GS["Paso 0: descarga Parquet + Products<br/>desde GCS al contexto Docker"]:::build
        DK["Paso 1: docker build<br/>COPY backend + src → imagen"]:::build
        GCR["Container Registry<br/>gcr.io/transpdd-tu-iniciales/transpdd-api"]:::build
    end

    subgraph PROD["Cloud Run (producción)"]
        REV["Nueva revisión<br/>ej. transpdd-api-00010-nh8"]:::run
        ENV["Env: ETL_ENGINE=python<br/>GCS_BUCKET=transpdd-pdd-datos"]:::run
    end

    PY --> PS1
    DCK --> PS1
    PS1 -->|"gcloud builds submit"| CB
    CB --> GS --> DK --> GCR
    PS1 -->|"gcloud run deploy"| REV
    GCR --> REV
    REV --> ENV
```

### Comando que dispara todo

```powershell
.\cloud\gcp\deploy-cloud-run.ps1
```

### Qué hace cada paso

| Paso | Herramienta | Resultado |
|------|-----------|-----------|
| 1 | `gcloud builds submit` | Sube el repo a Cloud Build |
| 2 | `cloudbuild.yaml` | Descarga datos base de GCS + construye imagen Docker |
| 3 | `Dockerfile` | Instala deps, copia `backend/` y `src/` dentro de la imagen |
| 4 | Push a GCR | Imagen versionada en `gcr.io/.../transpdd-api` |
| 5 | `gcloud run deploy` | Nueva revisión con 4 GiB RAM, timeout 300 s |

---

## 5. Dos motores ETL — Spark (curso) vs Python (Cloud Run)

```mermaid
flowchart LR
    subgraph BATCH["Batch — demostración PDD"]
        CSV1[(CSV en GCS)]
        DP3[Dataproc<br/>PySpark cluster]
        OUT1[(Parquet + ML)]
        CSV1 --> DP3 --> OUT1
    end

    subgraph ONLINE["Online — ingestión desde Vercel"]
        CSV2[(CSV en GCS)]
        CR3[Cloud Run<br/>Python streaming]
        OUT2[(Parquet + ML)]
        CSV2 --> CR3 --> OUT2
    end

    OUT1 --> GCS2[("GCS<br/>salida/processed")]
    OUT2 --> GCS2
    GCS2 --> API2[Cloud Run API<br/>sirve dashboard]
```

| Motor | Dónde corre | `meta.json` → `etl_engine` | Cuándo usarlo |
|-------|-------------|----------------------------|---------------|
| **Spark** | Dataproc (2 workers) | `spark-cluster` | Entrega del curso, ETL masivo distribuido |
| **Python** | Cloud Run | `python-streaming-gcs` | Subir CSV, Procesar, Eliminar tienda desde el front |

---

## 6. Deploy del frontend (Vercel) — separado de la API

```mermaid
flowchart LR
    GH["GitHub<br/>rama deploy"]
    VER["Vercel<br/>Root: frontend/"]
    ENV2["NEXT_PUBLIC_API_URL<br/>= URL Cloud Run"]
    USER2["Usuario"]

    GH -->|"git push → auto build"| VER
    ENV2 -.-> VER
    USER2 --> VER
    VER -->|"fetch API"| CR4[Cloud Run]
```

- **API:** se actualiza con `deploy-cloud-run.ps1` (Docker + Cloud Run).
- **Front:** se actualiza con **push a GitHub** → Vercel rebuild automático.
- Son **dos pipelines independientes**.

---

## Resumen en una frase

**Los datos viven en GCS; el código vive en imágenes Docker en Cloud Run; el usuario entra por Vercel; el ETL pesado de Spark corre en Dataproc; el reproceso desde el dashboard corre en Cloud Run.**
