# Databricks notebook source
# MAGIC %md
# MAGIC # ETL Spark (cluster) + ML — Transacciones supermercado
# MAGIC
# MAGIC 1. Sube el dataset a DBFS o monta Azure Storage (ver `docs/despliegue-azure-spark.md`).
# MAGIC 2. Clona este repo en **Repos** o `%pip install` dependencias y ajusta `REPO_ROOT`.
# MAGIC 3. Ejecuta todas las celdas.

# COMMAND ----------

import os
import subprocess
import sys

# Ajusta si clonaste en otro path (Workspace → Repos → tu usuario → repo)
REPO_ROOT = "/Workspace/Repos/<usuario>/Transacciones-de-supermercado-PDD"
os.chdir(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dataset en el driver (misma estructura que local)
# MAGIC Copia desde Storage montado, por ejemplo:
# MAGIC `dbutils.fs.cp("abfss://datos@.../DataSet/DataSet", "file:" + REPO_ROOT + "/DataSet/DataSet", recurse=True)`

# COMMAND ----------

# Descomenta y adapta si los CSV están en un mount:
# dbutils.fs.cp("/mnt/datos/DataSet/DataSet", f"file:{REPO_ROOT}/DataSet/DataSet", recurse=True)

# COMMAND ----------

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pandas", "pyarrow", "scikit-learn", "joblib"])

# COMMAND ----------

os.environ["ETL_ENGINE"] = "spark"
from src.etl.load_transactions import build_aggregates, load_meta

frames = build_aggregates(force=True)
print("Meta:", load_meta())
for name, df in frames.items():
    print(f"  {name}: {len(df):,} filas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Copiar salida a Storage (para App Service)
# MAGIC `processed` = `data/processed` con aggregates + ml

# COMMAND ----------

OUT = f"{REPO_ROOT}/data/processed"
# dbutils.fs.cp(f"file:{OUT}", "abfss://datos@<storage>.dfs.core.windows.net/salida/processed", recurse=True)
print("Listo. Sube esta carpeta a App Service (Kudu) o descarga ZIP:", OUT)
