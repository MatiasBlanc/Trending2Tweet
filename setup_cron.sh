#!/bin/bash
# Configura los cron jobs para los bots de trending2tweet
# Ejecutar: bash setup_cron.sh

PROJECT_DIR="/home/mblanc/workspaces/twitter/trending2Tweet"
PYTHON="/usr/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"

# Crear directorio de logs
mkdir -p "$LOG_DIR"

# Cron jobs:
# - main_news.py: 09:00 (noticias tech)
# - main_github.py: 12:00 (repos trending)
#
# Ejecución diaria (lunes a domingo)

CRON_JOBS="
0 9 * * * cd $PROJECT_DIR && $PYTHON main_news.py >> $LOG_DIR/news.log 2>&1
0 12 * * * cd $PROJECT_DIR && $PYTHON main_github.py >> $LOG_DIR/github.log 2>&1
"

# Agregar al crontab actual (sin duplicar)
(crontab -l 2>/dev/null | grep -v "main_news.py" | grep -v "main_github.py"; echo "$CRON_JOBS") | crontab -

echo "✅ Cron jobs configurados:"
echo ""
echo "   📰 News Bot:     09:00 (todos los días)"
echo "   🐙 GitHub Bot:   12:00 (todos los días)"
echo ""
echo "   Logs:"
echo "   - $LOG_DIR/news.log"
echo "   - $LOG_DIR/github.log"
echo ""
echo "Para ver los cron jobs: crontab -l"
echo "Para eliminar: crontab -e (y borra las líneas)"
