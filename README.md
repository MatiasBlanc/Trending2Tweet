# Trending2Tweet

Bot automatizado que genera y publica tweets sobre repos trending de GitHub y noticias de tecnología.

## Estructura

```
trending2tweet/
├── .env                        # Variables de entorno
├── config.py                   # Configuración centralizada
├── state_manager.py            # Memoria unificada (IDs procesados)
├── llm_client.py               # Motor de redacción con LLM
├── twitter_client.py           # Publicación en X/Twitter
├── sources/
│   ├── github_client.py        # Cliente API GitHub
│   └── hacker_news_client.py   # Cliente API Hacker News
├── prompts/
│   ├── prompt_github.txt       # Reglas de formato para repos
│   └── prompt_news.txt         # Reglas de formato para noticias
├── main_github.py              # Bot de GitHub (ejecutar al mediodía)
├── main_news.py                # Bot de noticias (ejecutar por la mañana)
├── main_github_manual.py       # Bot manual para un repo específico
├── metrics_db.py               # Base de datos SQLite para métricas
├── metrics_collector.py        # Recolector automático de métricas
└── dashboard.py                # Dashboard TUI para analytics
```

## Bots

### GitHub Trending Bot (`main_github.py`)

Busca los repos más populares del último mes en GitHub, genera tweets **sin URLs** y los publica automáticamente.

**IDs guardados como:** `gh_00000`

```bash
python main_github.py
```

### Tech News Bot (`main_news.py`)

Obtiene las noticias principales de Hacker News, genera tweets **sin URLs** y los publica automáticamente.

**IDs guardados como:** `nw_00000`

```bash
python main_news.py
```

### GitHub Manual Bot (`main_github_manual.py`)

Genera y publica un tweet para un repositorio específico. La URL se copia automáticamente al portapapeles.

```bash
python main_github_manual.py facebook/react
```

## Sistema de Métricas y Analytics

### Dashboard

Visualiza el rendimiento de todos los tweets publicados:

```bash
# Dashboard completo
python dashboard.py

# Historial de un tweet específico
python dashboard.py --historial 1234567890
```

El dashboard muestra:
- **Resumen general**: total tweets, likes, RTs, replies, impresiones
- **Rendimiento por fuente**: GitHub vs Noticias vs Manual
- **Rendimiento por prompt**: qué prompt genera mejor engagement
- **Rendimiento por estilo**: qué estilo de gancho funciona mejor (noticias)
- **Top tweets**: los tweets con mayor engagement score

### Recolector de Métricas

Recolecta automáticamente las métricas de engagement de los tweets publicados:

```bash
# Ejecutar manualmente
python metrics_collector.py

# Configurar cron job automático (cada 2 horas)
bash setup_metrics_cron.sh
```

### Engagement Score

El score se calcula con pesos configurables:

```
score = (likes × 1.0) + (retweets × 2.0) + (replies × 3.0) + (bookmarks × 2.5)
```

Los pesos se pueden ajustar en `.env`:
```env
ENG_WEIGHT_LIKES=1.0
ENG_WEIGHT_RTS=2.0
ENG_WEIGHT_REPLIES=3.0
ENG_WEIGHT_BOOKMARKS=2.5
```

### Ventanas de Colecta

El sistema recolecta métricas en estas ventanas de tiempo:
- **30 minutos**: métricas iniciales
- **2 horas**: engagement temprano
- **24 horas**: rendimiento del primer día
- **7 días**: rendimiento a largo plazo

### Base de Datos

SQLite local (`metrics.db`) con dos tablas:
- **tweets**: datos del tweet + métricas más recientes
- **metrics_history**: snapshots de métricas en el tiempo

## Flujo de URLs

Los tweets se publican **sin URLs** (para ahorrar costos de la API de Twitter). Las URLs se guardan en archivos de texto para que las agregues como comentario:

```
tweets/tweet_owner_repo_20260727_120000.txt
```

Contenido del archivo:
```
─── TWEET ───
[Texto del tweet sin URL]

─── URL (agregar como comentario) ───
https://github.com/owner/repo
```

## Configuración (.env)

```env
# GitHub API
GITHUB_TOKEN=ghp_xxx

# LLM (OpenAI-compatible)
LLM_API_KEY=xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.6

# Twitter/X API (OAuth 1.0a User Context)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

# Estado
STATE_FILE=state.json

# Control de longitud
FORCE_280_CHAR_TWEET=false

# Noticias
NEWS_SOURCE=hacker_news  # hacker_news | best
NEWS_LIMIT=5
NEWS_MIN_SCORE=50        # Filtrar ruido (solo 50+ puntos)

# Métricas
METRICS_DB_PATH=metrics.db
METRICS_COLLECT_INTERVAL=60  # minutos

# Pesos de engagement
ENG_WEIGHT_LIKES=1.0
ENG_WEIGHT_RTS=2.0
ENG_WEIGHT_REPLIES=3.0
ENG_WEIGHT_BOOKMARKS=2.5
```

## Ejecución Automatizada (cron)

```bash
# Bot de noticias a las 09:00
0 9 * * * cd /ruta/a/trending2tweet && python main_news.py >> logs/news.log 2>&1

# Bot de GitHub a las 12:00
0 12 * * * cd /ruta/a/trending2tweet && python main_github.py >> logs/github.log 2>&1

# Recolector de métricas cada 2 horas
0 */2 * * * cd /ruta/a/trending2tweet && python metrics_collector.py >> logs/metrics.log 2>&1
```

O usar el script de configuración:
```bash
bash setup_metrics_cron.sh
```

## Formato de IDs

- GitHub: `gh_{id_numerico}` (ej: `gh_1286080397`)
- Hacker News: `nw_{id_numerico}` (ej: `nw_49063754`)

Los IDs se almacenan en `state.json` para evitar duplicados.

## Filtro de Calidad (Noticias)

El parámetro `NEWS_MIN_SCORE` filtra noticias con puntuación baja:
- `0`: Sin filtro (todas las noticias)
- `50`: Moderado (recomendado)
- `100`: Estricto (solo las mejores)
