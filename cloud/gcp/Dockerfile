FROM python:3.11-slim

WORKDIR /app
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend ./backend
COPY src ./src
# Snapshot inicial (GCS es la fuente de verdad si GCS_BUCKET está definido):
COPY data/processed ./data/processed
# Categories.csv para recomendador (cloudbuild lo descarga de GCS antes del build):
RUN mkdir -p DataSet/DataSet/Products
COPY DataSet/DataSet/Products ./DataSet/DataSet/Products

ENV ETL_ENGINE=python
ENV GCS_BUCKET=transpdd-pdd-datos
ENV GCS_DATA_PREFIX=DataSet/DataSet
ENV GCS_OUTPUT_PREFIX=salida/processed
ENV PORT=8080
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
