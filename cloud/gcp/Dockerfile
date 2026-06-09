FROM python:3.11-slim

WORKDIR /app
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend ./backend
COPY src ./src
COPY cloud/dataproc ./cloud/dataproc
# Agregados embebidos en la imagen; en producción GCS tiene prioridad.
COPY data/processed ./data/processed
# Catálogo de productos (también se obtiene de GCS en el build de Cloud Build).
RUN mkdir -p DataSet/DataSet/Products
COPY DataSet/DataSet/Products ./DataSet/DataSet/Products

ENV ETL_ENGINE=python
ENV GCS_BUCKET=transpdd-pdd-datos
ENV GCS_DATA_PREFIX=DataSet/DataSet
ENV GCS_OUTPUT_PREFIX=salida/processed
ENV PORT=8080
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
