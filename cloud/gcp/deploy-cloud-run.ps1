# Build imagen + deploy Cloud Run con GCS y 2Gi RAM
param(
    [string]$Project = "transpdd-tu-iniciales",
    [string]$Region = "us-central1",
    [string]$Service = "transpdd-api"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

Write-Host "==> Cloud Build"
gcloud builds submit . --config=cloud/gcp/cloudbuild.yaml --project=$Project

Write-Host "==> Cloud Run deploy"
gcloud run deploy $Service `
  --image "gcr.io/$Project/transpdd-api" `
  --region $Region `
  --project $Project `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --set-env-vars "ETL_ENGINE=python,GCS_BUCKET=transpdd-pdd-datos,GCS_DATA_PREFIX=DataSet/DataSet,GCS_OUTPUT_PREFIX=salida/processed"

Write-Host "==> Listo. Prueba /api/health (gcs_enabled: true)"
