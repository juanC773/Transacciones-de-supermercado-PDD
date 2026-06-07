FROM python:3.11-slim

WORKDIR /app
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend ./backend
COPY src ./src
# Incluir data/processed/ en el build (generado por ETL local o Dataproc):
COPY data/processed ./data/processed

ENV ETL_ENGINE=python
ENV PORT=8080
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
