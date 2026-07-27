#!/bin/bash
# Script para configurar el cron job de recolección de métricas
# Ejecutar: bash setup_metrics_cron.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$(which python3)"
COLLECTOR_SCRIPT="$SCRIPT_DIR/metrics_collector.py"
LOG_FILE="$SCRIPT_DIR/logs/metrics_collector.log"

# Crear directorio de logs si no existe
mkdir -p "$SCRIPT_DIR/logs"

# Configurar cron job para ejecutar cada 2 horas
CRON_JOB="0 */2 * * * cd $SCRIPT_DIR && $PYTHON_PATH $COLLECTOR_SCRIPT >> $LOG_FILE 2>&1"

# Verificar si ya existe el cron job
if crontab -l 2>/dev/null | grep -q "metrics_collector.py"; then
    echo "⚠️  Ya existe un cron job para metrics_collector.py"
    echo "Cron jobs actuales:"
    crontab -l | grep metrics_collector
else
    # Agregar el cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job configurado para ejecutar cada 2 horas"
    echo "   Comando: $CRON_JOB"
fi

echo ""
echo "Para ver todos los cron jobs: crontab -l"
echo "Para editar cron jobs: crontab -e"
echo "Para eliminar este cron job: crontab -l | grep -v metrics_collector | crontab -"
