#!/bin/bash
# Ejecutar en el nodo master de Dataproc (tras SSH).
# Requiere: src/ y DataSet/DataSet/ en el directorio del proyecto.
set -euo pipefail

cd "${HOME}/Transacciones-de-supermercado-PDD" 2>/dev/null || cd /home/Admin/Transacciones-de-supermercado-PDD

pip install -q pandas pyarrow scikit-learn joblib

export ETL_ENGINE=spark
python3 -m src.etl.load_transactions

echo "ETL listo. meta.json:"
cat data/processed/aggregates/meta.json
