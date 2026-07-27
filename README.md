# Trending2Tweet

Bot automatizado que genera y publica tweets sobre repos trending de GitHub y noticias de tecnología.

## Estructura

```
trending2tweet/
├── .env                        # Variables de entorno
├── config.py                   # Configuración centralizada
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
├── metrics_db.py               # Base de datos SQLite (estado + métricas)
├── metrics_collector.py        # Recolector automático de métricas
├── scheduler.py                # Worker que ejecuta collector automáticamente
├── migrate_state.py            # Migración de state.json → metrics.db (una vez)
├── tui.py                      # Dashboard interactivo (textual)
├── tui                         # Alias para ejecutar ./tui
├── Procfile                    # Configuración Heroku
├── requirements.txt            # Dependencias Python
└── runtime.txt                 # Versión de Python
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
# Dashboard interactivo (RECOMENDADO)
./tui
python tui.py

# Dashboard estático (rich)
python dashboard.py

# Historial de un tweet específico
python dashboard.py --historial 1234567890
```

#### TUI Interactiva (`tui.py`)

Atajos de teclado:
- `1/2/3`: Ordenar por fecha/likes/score
- `f`: Filtrar por fuente (github/news/manual/todas)
- `r`: Refrescar datos
- `Enter`: Ver detalle de un tweet seleccionado
- `Escape/q`: Volver/Salir

El dashboard muestra:
- **Resumen general**: total tweets, likes, RTs, replies, impresiones
- **Tweets**: tabla navegable con todas las métricas
- **Rendimiento por prompt**: qué prompt genera mejor engagement
- **Rendimiento por estilo**: qué estilo de gancho funciona mejor (noticias)
- **Historial**: evolución temporal de métricas por tweet

### Migración de state.json

Si tenías un `state.json` anterior, ejecuta la migración una sola vez:

```bash
python migrate_state.py
```

Esto moverá todos los IDs a `metrics.db` y creará un backup de `state.json`.

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

## Ejecución Automatizada

### Opción 1: Scheduler local (recomendado para desarrollo)

```bash
# Ejecutar el scheduler como worker
python scheduler.py
```

El scheduler:
- Revisa cada 5 minutos si hay tweets pendientes
- Colecta métricas automáticamente a los 30min, 2h, 24h y 7 días
- Se ejecuta en loop continuo hasta Ctrl+C

### Opción 2: Heroku (producción)

#### 1. Crear app de Heroku

```bash
heroku create trending2tweet-prod
```

#### 2. Configurar variables de entorno

```bash
bash setup_heroku.sh trending2tweet-prod
```

O manualmente:

```bash
heroku config:set GITHUB_TOKEN=xxx LLM_API_KEY=xxx TWITTER_API_KEY=xxx ... --app trending2tweet-prod
```

#### 3. Deployar

```bash
# Agregar remote de Heroku
heroku git:remote -a trending2tweet-prod

# Push a Heroku
git push heroku feature/metrics-dashboard:main
```

#### 4. Iniciar el worker

```bash
# El worker ejecuta el scheduler automáticamente
heroku ps:scale worker=1 --app trending2tweet-prod
```

#### 5. Ver logs

```bash
heroku logs --tail --app trending2tweet-prod
```

#### 6. Ejecutar bots manualmente

```bash
# Ejecutar bot de GitHub
heroku run python main_github.py --app trending2tweet-prod

# Ejecutar bot de noticias
heroku run python main_news.py --app trending2tweet-prod

# Ejecutar bot manual
heroku run python main_github_manual.py facebook/react --app trending2tweet-prod
```

### Opción 3: Railway (alternativa a Heroku)

```bash
# Instalar CLI de Railway
npm install -g @railway/cli

# Login
railway login

# Crear proyecto
railway init

# Deployar
railway up

# Configurar variables
railway variables set GITHUB_TOKEN=xxx ...
```

### Opción 4: VPS con systemd (DigitalOcean, Linode, etc.)

```bash
# Crear servicio systemd
sudo nano /etc/systemd/system/trending2tweet.service
```

```ini
[Unit]
Description=Trending2Tweet Scheduler
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/trending2tweet
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y arrancar
sudo systemctl enable trending2tweet
sudo systemctl start trending2tweet

# Ver estado
sudo systemctl status trending2tweet
```

## Formato de IDs

- GitHub: `gh_{id_numerico}` (ej: `gh_1286080397`)
- Hacker News: `nw_{id_numerico}` (ej: `nw_49063754`)

Los IDs se almacenan en `metrics.db` para evitar duplicados.

## Filtro de Calidad (Noticias)

El parámetro `NEWS_MIN_SCORE` filtra noticias con puntuación baja:
- `0`: Sin filtro (todas las noticias)
- `50`: Moderado (recomendado)
- `100`: Estricto (solo las mejores)
