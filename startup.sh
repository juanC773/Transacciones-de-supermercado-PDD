#!/bin/bash
# Azure App Service (Linux): comando de inicio en Configuración → Comando de inicio
# o: chmod +x startup.sh && ./startup.sh
set -e
cd /home/site/wwwroot 2>/dev/null || true
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
