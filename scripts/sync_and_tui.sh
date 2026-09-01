#!/bin/bash
# Ejecutar todos los bots para generar borradores en Obsidian
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=========================================="
echo "  Generando borradores para Obsidian..."
echo "=========================================="

echo -e "\n[1/4] 🐙 GitHub Trending..."
python -m bots.github_trending 1

echo -e "\n[2/4] 📰 Tech News..."
python -m bots.news 1

echo -e "\n[3/4] 💻 Code News..."
python -m bots.codigo 1

echo -e "\n[4/4] ⌨️  Teclados..."
python -m bots.teclados 1

echo -e "\n[+] 📦 Verificando archivados..."
python -m bots.archivar

echo -e "\n✅ ¡Listo! Revisa tu bóveda en ~/Obsidian/Twitter/bot/"
