# Trending2Tweet

Bot que genera tweets automáticos sobre repos de GitHub trending y noticias tech de Hacker News.

## Instalación

```bash
# Clonar repositorio
git clone <url>
cd trending2Tweet

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Copiar `.env.example` a `.env` y configurar:

```bash
cp .env.example .env
```

Variables requeridas:
- `GITHUB_TOKEN`: Token de GitHub API
- `LLM_API_KEY`: API key del LLM (OpenAI compatible)
- `LLM_BASE_URL`: URL base del LLM
- `LLM_MODEL`: Modelo a usar
- `OBSIDIAN_VAULT_PATH`: Ruta a la bóveda de Obsidian

## Uso

### Bot Manual de GitHub
Genera un tweet para un repo específico:
```bash
python -m bots.github_manual facebook/react
```

### Bot de GitHub Trending
Genera tweets para repos trending:
```bash
python -m bots.github_trending
```

### Bot de Noticias Tech
Genera tweets para noticias de Hacker News:
```bash
python -m bots.news
```

### Bot de Mejora de Tweets
Mejora tweets manuales con IA para hacerlos más virales:
```bash
python -m bots.mejorar_tweet
```

Para más detalles, ver [docs/mejorar-tweet.md](docs/mejorar-tweet.md).

## Estructura de Obsidian

Los tweets se guardan en la bóveda de Obsidian con esta estructura:

```
T2T/
├── borradores/    ← Tweets generados (pendientes de revisión)
├── listos/        ← Tweets editados y listos para publicar
└── publicados/    ← Tweets ya publicados en Twitter
attachments/       ← Imágenes generadas
```

### Flujo de trabajo

1. Ejecutar el bot → genera borrador en `T2T/borradores/`
2. Abrir Obsidian y revisar el borrador
3. Editar el tweet si es necesario
4. Mover a `T2T/listos/` cuando esté listo
5. Publicar manualmente en Twitter

## Estructura del Proyecto

```
trending2Tweet/
├── bots/
│   ├── github_manual.py    ← Bot manual para repos específicos
│   ├── github_trending.py  ← Bot automático para repos trending
│   ├── news.py             ← Bot de noticias Hacker News
│   └── mejorar_tweet.py    ← Bot para mejorar tweets manuales con IA
├── src/
│   ├── config.py           ← Configuración centralizada
│   ├── llm_client.py       ← Cliente para generar tweets con LLM
│   ├── obsidian_vault.py   ← Gestión de bóveda de Obsidian
│   └── card_generator.py   ← Generador de tarjetas visuales
├── sources/
│   ├── github_client.py    ← Cliente de GitHub API
│   └── hacker_news_client.py ← Cliente de Hacker News
├── db/
│   └── metrics_db.py       ← Base de datos de métricas
├── prompts/
│   ├── prompt_github.txt      ← Prompt para tweets de GitHub
│   ├── prompt_news.txt        ← Prompt para tweets de noticias
│   └── prompt_mejorar_tweet.txt ← Prompt para mejorar tweets
├── docs/
│   └── mejorar-tweet.md       ← Documentación del bot de mejora
├── scripts/
│   ├── run_manual.sh       ← Script para bot manual
│   ├── sync_and_tui.sh     ← Script para ejecutar todos los bots
│   └── setup_cron.sh       ← Configurar cron jobs
└── .env.example            ← Ejemplo de variables de entorno
```

## Scripts de Shell

```bash
# Ejecutar bot manual
./scripts/run_manual.sh facebook/react

# Ejecutar todos los bots
./scripts/sync_and_tui.sh

# Configurar cron jobs
./scripts/setup_cron.sh
```

## Personalización

### Cambiar el LLM

Editar en `.env`:
```bash
LLM_API_KEY=tu-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### Cambiar el branding de las tarjetas

Editar en `.env`:
```bash
CARD_BRAND_NAME=tu_usuario
```

### Desactivar imágenes

Editar en `.env`:
```bash
ENABLE_TWEET_IMAGES=false
```

## Licencia

MIT
