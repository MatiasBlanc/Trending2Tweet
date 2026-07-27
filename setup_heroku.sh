#!/bin/bash
# Script para configurar Heroku con todas las variables necesarias
# Ejecutar: bash setup_heroku.sh

echo "━"
echo "  Configurando Heroku para Trending2Tweet"
echo "━"

# Verificar si hay un app de Heroku
if [ -z "$1" ]; then
    echo "Uso: bash setup_heroku.sh <nombre-app>"
    echo "Ejemplo: bash setup_heroku.sh trending2tweet-prod"
    exit 1
fi

APP_NAME=$1

echo "  App: $APP_NAME"
echo ""

# Pedir variables de entorno
read -p "  GITHUB_TOKEN: " GITHUB_TOKEN
read -p "  LLM_API_KEY: " LLM_API_KEY
read -p "  LLM_BASE_URL (default: https://api.openai.com/v1): " LLM_BASE_URL
LLM_BASE_URL=${LLM_BASE_URL:-https://api.openai.com/v1}
read -p "  LLM_MODEL (default: gpt-4o-mini): " LLM_MODEL
LLM_MODEL=${LLM_MODEL:-gpt-4o-mini}
read -p "  TWITTER_API_KEY: " TWITTER_API_KEY
read -p "  TWITTER_API_SECRET: " TWITTER_API_SECRET
read -p "  TWITTER_ACCESS_TOKEN: " TWITTER_ACCESS_TOKEN
read -p "  TWITTER_ACCESS_SECRET: " TWITTER_ACCESS_SECRET

echo ""
echo "  Configurando variables en Heroku..."

heroku config:set \
    GITHUB_TOKEN="$GITHUB_TOKEN" \
    LLM_API_KEY="$LLM_API_KEY" \
    LLM_BASE_URL="$LLM_BASE_URL" \
    LLM_MODEL="$LLM_MODEL" \
    TWITTER_API_KEY="$TWITTER_API_KEY" \
    TWITTER_API_SECRET="$TWITTER_API_SECRET" \
    TWITTER_ACCESS_TOKEN="$TWITTER_ACCESS_TOKEN" \
    TWITTER_ACCESS_SECRET="$TWITTER_ACCESS_SECRET" \
    --app "$APP_NAME"

echo ""
echo "  ✅ Variables configuradas"
echo ""
echo "  Para deployar:"
echo "    git push heroku feature/metrics-dashboard:main"
echo ""
echo "  Para iniciar el worker:"
echo "    heroku ps:scale worker=1 --app $APP_NAME"
echo ""
echo "  Para ver logs:"
echo "    heroku logs --tail --app $APP_NAME"
