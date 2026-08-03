#!/bin/bash
# Configurar cron jobs para los bots

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Crear archivo de cron
CRON_FILE="/tmp/trending2tweet_cron"

cat > "$CRON_FILE" << EOF
# GitHub Trending Bot - cada 6 horas
0 */6 * * * cd $PROJECT_DIR && python -m bots.github_trending >> logs/github.log 2>&1

# News Bot - cada 2 horas
0 */2 * * * cd $PROJECT_DIR && python -m bots.news >> logs/news.log 2>&1
EOF

# Instalar cron
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo "Cron jobs instalados:"
crontab -l
