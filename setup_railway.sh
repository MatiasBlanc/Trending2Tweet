#!/bin/bash
# Script para deployar en Railway
# Ejecutar: bash setup_railway.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚂 Setup Railway - Trending2Tweet"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verificar si Railway CLI está instalado
if ! command -v railway &> /dev/null; then
    echo "  ❌ Railway CLI no está instalado."
    echo ""
    echo "  Instalar con:"
    echo "    npm install -g @railway/cli"
    echo ""
    echo "  O con curl:"
    echo "    curl -fsSL https://railway.app/install.sh | sh"
    echo ""
    exit 1
fi

echo "  ✅ Railway CLI encontrado"
echo ""

# Login
echo "  📦 Paso 1: Login en Railway"
echo "  (Se abrirá el navegador)"
echo ""
railway login
echo ""

# Crear proyecto
echo "  📦 Paso 2: Crear proyecto"
read -p "  Nombre del proyecto (default: trending2tweet): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-trending2tweet}

railway init --name "$PROJECT_NAME"
echo ""

# Conectar a GitHub (opcional)
echo "  📦 Paso 3: ¿Conectar a GitHub para auto-deploy?"
read -p "  ¿Conectar repo de GitHub? (s/n, default: s): " CONNECT_GITHUB
CONNECT_GITHUB=${CONNECT_GITHUB:-s}

if [[ "$CONNECT_GITHUB" == "s" || "$CONNECT_GITHUB" == "si" ]]; then
    echo ""
    echo "  ℹ️  Se abrirá Railway para conectar tu repo de GitHub"
    echo "  Selecciona: MatiasBlanc/Trending2Tweet"
    echo "  Branch: feature/metrics-dashboard"
    echo ""
    railway open
    echo ""
    read -p "  Presiona Enter cuando hayas conectado el repo..."
fi

# Configurar variables de entorno
echo ""
echo "  📦 Paso 4: Variables de entorno"
echo "  (Tus credenciales secretas)"
echo ""

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
echo "  ⚙️  Configurando variables..."

railway variables set \
    GITHUB_TOKEN="$GITHUB_TOKEN" \
    LLM_API_KEY="$LLM_API_KEY" \
    LLM_BASE_URL="$LLM_BASE_URL" \
    LLM_MODEL="$LLM_MODEL" \
    TWITTER_API_KEY="$TWITTER_API_KEY" \
    TWITTER_API_SECRET="$TWITTER_API_SECRET" \
    TWITTER_ACCESS_TOKEN="$TWITTER_ACCESS_TOKEN" \
    TWITTER_ACCESS_SECRET="$TWITTER_ACCESS_SECRET" \
    FORCE_280_CHAR_TWEET="true" \
    NEWS_SOURCE="hacker_news" \
    NEWS_LIMIT="5" \
    NEWS_MIN_SCORE="50" \
    METRICS_DB_PATH="metrics.db"

echo ""
echo "  ✅ Variables configuradas"
echo ""

# Deployar
echo "  📦 Paso 5: Deployar"
read -p "  ¿Deployar ahora? (s/n, default: s): " DEPLOY_NOW
DEPLOY_NOW=${DEPLOY_NOW:-s}

if [[ "$DEPLOY_NOW" == "s" || "$DEPLOY_NOW" == "si" ]]; then
    echo ""
    echo "  🚀 Deployando..."
    railway up
    echo ""
    echo "  ✅ Deploy iniciado"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Setup completado"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Próximos pasos:"
echo ""
echo "  1. Abrir Railway dashboard:"
echo "     railway open"
echo ""
echo "  2. Configurar el Worker (scheduler):"
echo "     - En Railway → Settings → Service"
echo "     - Agregar servicio 'worker'"
echo "     - Start Command: python scheduler.py"
echo ""
echo "  3. Ejecutar bots manualmente:"
echo "     railway run python main_github.py"
echo "     railway run python main_news.py"
echo "     railway run python main_github_manual.py usuario/repo"
echo ""
echo "  4. Ver logs:"
echo "     railway logs"
echo ""
