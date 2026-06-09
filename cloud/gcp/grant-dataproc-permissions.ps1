# Concede a Cloud Run permiso para enviar jobs a Dataproc (ejecutar una vez).
param(
    [string]$Project = "transpdd-tu-iniciales",
    [string]$Region = "us-central1",
    [string]$Service = "transpdd-api"
)

$ErrorActionPreference = "Stop"
$ProjectNumber = gcloud projects describe $Project --format="value(projectNumber)"
$RunSa = "$ProjectNumber-compute@developer.gserviceaccount.com"

Write-Host "Cuenta de servicio Cloud Run (default): $RunSa"
gcloud projects add-iam-policy-binding $Project `
  --member="serviceAccount:$RunSa" `
  --role="roles/dataproc.editor" `
  --quiet

Write-Host "Listo. Redespliega la API si cambiaste variables: .\cloud\gcp\deploy-cloud-run.ps1"
