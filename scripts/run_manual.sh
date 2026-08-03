#!/bin/bash
# Ejecutar bot manual de GitHub
# Uso: ./scripts/run_manual.sh facebook/react

if [ -z "$1" ]; then
    echo "Uso: $0 user/repo"
    echo "Ejemplo: $0 facebook/react"
    exit 1
fi

cd "$(dirname "$0")/.."
python -m bots.github_manual "$1"
