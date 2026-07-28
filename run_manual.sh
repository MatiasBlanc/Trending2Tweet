#!/bin/bash
# Ejecuta el bot manual para un repo específico en Railway
# Uso: ./run_manual.sh owner/repo

set -e

if [ -z "$1" ]; then
    echo "❌ Uso: ./run_manual.sh owner/repo"
    echo "   Ejemplo: ./run_manual.sh facebook/react"
    exit 1
fi

REPO="$1"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🐙 Publicando repo: $REPO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

railway run python main_github_manual.py "$REPO"
