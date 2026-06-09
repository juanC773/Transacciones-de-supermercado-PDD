"""ETL batch con PySpark (local[*] o cluster Databricks/Synapse). Invocado desde load_transactions."""
from __future__ import annotations
import json
import os
import pathlib
import shutil
import socket
from datetime import datetime
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType
from src.etl.load_transactions import (
    AGG_DIR,
    META_FILE,
    RAW_TRANS,
    _load_categories,
    _load_product_to_categories,
    load_aggregates,
    resolve_ticket_categories,
)

# Mapa SKU -> categoría (tiendas 103, 107, 110); se carga una vez por corrida ETL.
_PRODUCT_MAP: dict[int, list[int]] | None = None


def _product_map() -> dict[int, list[int]]:
    global _PRODUCT_MAP
    if _PRODUCT_MAP is None:
        _PRODUCT_MAP = _load_product_to_categories()
    return _PRODUCT_MAP

# Columnas de la tabla "expandida" (una fila por categoría en cada ticket).
ROW_SCHEMA = StructType(
    [
        StructField("fecha", StringType(), False),
        StructField("id_tienda", IntegerType(), False),
        StructField("id_cliente", IntegerType(), False),
        StructField("id_categoria", IntegerType(), False),
        StructField("tx_key", StringType(), False),       # ID único del ticket
        StructField("cantidad_tx", IntegerType(), False),  # ítems totales del ticket
    ]
)


def _on_spark_cluster() -> bool:
    """Cluster gestionado (Dataproc, Databricks, Synapse): no usar local[*]."""
    if os.environ.get("DATAPROC_VERSION") or os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        return True
    if os.environ.get("SYNAPSE_SPARK_POOL_USAGE"):
        return True
    # En Dataproc, python3 -m a veces no exporta DATAPROC_VERSION; el hostname termina en -m o -w-N.
    host = socket.gethostname()
    return host.endswith("-m") or "-w-" in host or host.endswith("-w")


def _gcs_bucket() -> str:
    return os.environ.get("GCS_BUCKET", "transpdd-pdd-datos").strip()


def _tran_input_for_spark(tran_files: list) -> str | list[str]:
    """
    Dataproc: workers no ven /home/Admin del master → leer CSV desde GCS.
    Local: rutas file:// en disco.
    """
    if _on_spark_cluster():
        prefix = os.environ.get("GCS_TRANS_PREFIX", "DataSet/DataSet/Transactions").strip("/")
        path = f"gs://{_gcs_bucket()}/{prefix}/*_Tran.csv"
        print(f"Dataproc: leyendo transacciones desde {path}")
        return path
    return [pathlib.Path(f).resolve().as_uri() for f in tran_files]


def _ship_src_to_workers(spark: SparkSession) -> None:
    """Workers no tienen el repo; empaquetar src/ y enviarlo con addPyFile."""
    if os.environ.get("PDD_ETL_FROM_GCS"):
        return  # Job enviado desde Cloud Run: python_file_uris ya incluye pdd_src.zip
    root = pathlib.Path(__file__).resolve().parent.parent.parent
    zip_path = "/tmp/pdd_src.zip"
    shutil.make_archive("/tmp/pdd_src", "zip", root, "src")
    spark.sparkContext.addPyFile(zip_path)


def _spark_session() -> SparkSession:
    """Local: local[*]. Nube: sesión del cluster (driver + executors)."""
    builder = SparkSession.builder.appName("TransaccionesSupermercado")
    if _on_spark_cluster():
        return (
            builder.config("spark.sql.shuffle.partitions", "16")
            .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
            .getOrCreate()
        )
    return (
        builder.master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )


def _line_to_rows(
    line: str,
    source: str,
    line_no: int,
    prod_map: dict[int, list[int]] | None = None,
) -> list[tuple]:
    """
    Convierte UNA línea del CSV en VARIAS filas (una por categoría comprada).

    Ejemplo de línea:
      2013-01-15|102|5001|3 7 7 12
    Resultado: 4 tuplas (cat 3, 7, 7, 12) con el mismo tx_key y cantidad_tx=4.
    """
    line = (line or "").strip()
    if not line:
        return []

    # Separador del dataset del curso: pipe |
    parts = line.split("|")
    if len(parts) < 4:
        return []

    fecha, tienda_s, cliente_s, productos_str = parts[0], parts[1], parts[2], parts[3]
    try:
        tienda = int(tienda_s)
        cliente = int(cliente_s)
    except ValueError:
        return []

    # "3 7 7 12" -> categorías 1-50 (tienda 102 directo; otras vía ProductCategory.csv)
    raw_ids = [int(p) for p in productos_str.split() if p.isdigit()]
    cats = resolve_ticket_categories(raw_ids, tienda, prod_map or _product_map())
    if not cats:
        return []

    # tx_key identifica el ticket para contar transacciones sin duplicar filas
    tx_key = f"{source}:{line_no}:{fecha}:{tienda}:{cliente}"
    cantidad_tx = len(cats)  # unidades en ese ticket (para boxplot después)

    return [(fecha, tienda, cliente, cat_id, tx_key, cantidad_tx) for cat_id in cats]


def build_aggregates_spark(force: bool = False) -> dict[str, pd.DataFrame]:
    """
    Función principal del ETL Spark.
    Si ya existe .done y force=False, no reprocesa: solo lee Parquet.
    """
    AGG_DIR.mkdir(parents=True, exist_ok=True)
    marker = AGG_DIR / ".done"

    # --- Atajo: ETL ya corrido antes ---
    if marker.exists() and not force:
        return load_aggregates()

    # Nombres de categorías (Categories.csv) para el gráfico de donut/top
    if _on_spark_cluster() and os.environ.get("GCS_BUCKET"):
        from src.etl.load_transactions import RAW_PROD
        from src.storage.gcs import sync_products_from_gcs

        sync_products_from_gcs(RAW_PROD)

    cats_map = _load_categories()
    tran_files = sorted(RAW_TRANS.glob("*_Tran.csv"))
    if not tran_files and not _on_spark_cluster():
        raise FileNotFoundError(f"No se encontraron archivos *_Tran.csv en {RAW_TRANS}")

    spark = _spark_session()
    spark.sparkContext.setLogLevel("WARN")
    if _on_spark_cluster():
        _ship_src_to_workers(spark)
    bc_prod_map = spark.sparkContext.broadcast(_product_map())
    try:
        # =================================================================
        # PASO 1: LEER CSV Y PARSEAR
        # =================================================================
        # Lee cada archivo como texto (una fila = una transacción cruda)
        raw = spark.read.text(_tran_input_for_spark(tran_files)).withColumn(
            "source_file", F.input_file_name()
        )

        # flatMap: por cada línea llama _line_to_rows y aplana todas las tuplas
        parsed = raw.rdd.zipWithIndex().flatMap(
            lambda row_idx: _line_to_rows(
                row_idx[0][0],  # contenido de la línea
                row_idx[0][1].split("/")[-1] if "/" in row_idx[0][1] else row_idx[0][1],
                int(row_idx[1]),  # número de línea
                bc_prod_map.value,
            )
        )

        # Tabla Spark con todas las filas expandidas
        df = spark.createDataFrame(parsed, schema=ROW_SCHEMA).withColumn(
            "fecha", F.to_date("fecha")
        )
        df.cache()  # se reutiliza en varios groupBy

        # =================================================================
        # PASO 2: AGREGACIONES (resúmenes para el dashboard)
        # =================================================================

        # por_dia -> gráfico de línea temporal, heatmap día/mes
        por_dia = (
            df.groupBy("fecha", "id_tienda")
            .agg(
                F.countDistinct("tx_key").alias("n_transacciones"),  # tickets únicos
                F.count("*").alias("unidades"),  # cada fila = 1 unidad de categoría
            )
            .toPandas()
        )
        if not por_dia.empty:
            por_dia["fecha"] = pd.to_datetime(por_dia["fecha"])
            por_dia["mes"] = por_dia["fecha"].dt.month
            por_dia["dia_semana"] = por_dia["fecha"].dt.day_name()

        # por_semana -> gráfico semanal (weekofyear evita patrón yyyy-'W'ww roto en Spark 3+)
        por_semana = (
            df.withColumn(
                "anio_semana",
                F.concat(
                    F.year("fecha").cast("string"),
                    F.lit("-W"),
                    F.format_string("%02d", F.weekofyear("fecha")),
                ),
            )
            .groupBy("anio_semana", "id_tienda")
            .agg(
                F.count("*").alias("unidades"),
                F.countDistinct("tx_key").alias("n_transacciones"),
            )
            .toPandas()
        )

        # por_categoria -> top categorías y donut (sin precios, solo volumen)
        por_categoria = (
            df.groupBy("fecha", "id_tienda", "id_categoria")
            .agg(F.count("*").alias("cantidad"))
            .toPandas()
        )
        if not por_categoria.empty:
            por_categoria["nombre_categoria"] = por_categoria["id_categoria"].map(
                lambda c: cats_map.get(int(c), f"Categoría {c}")
            )
            por_categoria["fecha"] = pd.to_datetime(por_categoria["fecha"])

        # por_cliente -> ranking clientes, matriz de correlación
        por_cliente = (
            df.groupBy("id_tienda", "id_cliente")
            .agg(
                F.min("fecha").alias("fecha_min"),
                F.max("fecha").alias("fecha_max"),
                F.countDistinct("tx_key").alias("n_transacciones"),
                F.count("*").alias("unidades"),
                F.countDistinct("id_categoria").alias("n_categorias"),
            )
            .toPandas()
        )
        if not por_cliente.empty:
            por_cliente["fecha_min"] = pd.to_datetime(por_cliente["fecha_min"])
            por_cliente["fecha_max"] = pd.to_datetime(por_cliente["fecha_max"])
            dias = (por_cliente["fecha_max"] - por_cliente["fecha_min"]).dt.days + 1
            por_cliente["dias_activos"] = dias.clip(lower=1)
            por_cliente["frecuencia_semanal"] = por_cliente["n_transacciones"] / (
                por_cliente["dias_activos"] / 7
            )

        # por_tx -> una fila por ticket; alimenta el BOXPLOT por cliente
        tx_df = (
            df.select("fecha", "id_tienda", "id_cliente", "tx_key", "cantidad_tx")
            .dropDuplicates(["tx_key"])  # quitar duplicados por categoría
            .withColumnRenamed("cantidad_tx", "cantidad")
            .withColumn("mes", F.month("fecha"))
            .withColumn("dia_semana", F.date_format("fecha", "EEEE"))
        )
        por_tx = tx_df.toPandas()
        if not por_tx.empty:
            por_tx["fecha"] = pd.to_datetime(por_tx["fecha"])
            por_tx["id_transaccion"] = por_tx["tx_key"]

        # Canastas: categorías únicas por ticket (recomendador)
        canastas_sp = (
            df.groupBy("fecha", "id_tienda", "id_cliente", "tx_key")
            .agg(
                F.concat_ws(
                    " ",
                    F.sort_array(F.collect_set(F.col("id_categoria").cast("string"))),
                ).alias("categorias")
            )
        )
        canastas = canastas_sp.withColumnRenamed("tx_key", "id_transaccion").toPandas()
        if not canastas.empty:
            canastas["fecha"] = pd.to_datetime(canastas["fecha"])

        frames = {
            "por_dia": por_dia,
            "por_semana": por_semana,
            "por_categoria": por_categoria,
            "por_cliente": por_cliente,
            "por_tx": por_tx,
            "canastas": canastas,
        }

        # =================================================================
        # PASO 3: GUARDAR EN DISCO (la API leerá estos archivos)
        # =================================================================
        for name, frame in frames.items():
            if frame is not None and not frame.empty:
                frame.to_parquet(AGG_DIR / f"{name}.parquet", index=False)

        # meta.json: totales y rango de fechas para el sidebar del frontend
        meta = {
            "total_unidades": int(df.count()),
            "total_transacciones": int(len(por_tx)) if not por_tx.empty else 0,
            "total_clientes": (
                int(por_cliente[["id_tienda", "id_cliente"]].drop_duplicates().shape[0])
                if not por_cliente.empty
                else 0
            ),
            "fecha_min": str(por_dia["fecha"].min()) if not por_dia.empty else "",
            "fecha_max": str(por_dia["fecha"].max()) if not por_dia.empty else "",
            "tiendas": sorted(int(x) for x in por_dia["id_tienda"].unique()) if not por_dia.empty else [],
            "generado": datetime.now().isoformat(),
            "etl_engine": "spark-cluster" if _on_spark_cluster() else "spark-local",
        }
        META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        marker.touch()  # marca que el ETL terminó OK
        from src.etl.load_transactions import _train_ml_safe, _sync_outputs_to_gcs
        _train_ml_safe(frames)
        if _on_spark_cluster() and os.environ.get("GCS_BUCKET"):
            _sync_outputs_to_gcs()
        return frames
    finally:
        # En notebook Databricks no cerrar la sesión compartida del cluster.
        if not _on_spark_cluster():
            spark.stop()
