#!/bin/bash
# Ejecutar bots de forma secuencial

cd "$(dirname "$0")/.."

echo "Ejecutando GitHub Trending Bot..."
python -m bots.github_trending

echo ""
echo "Ejecutando News Bot..."
python -m bots.news
