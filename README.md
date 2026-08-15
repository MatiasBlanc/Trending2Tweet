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
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN` y `TWITTER_ACCESS_SECRET`: Credenciales de X
- `OBSIDIAN_VAULT_PATH`: Ruta de la bóveda para los borradores manuales

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

### Bots temáticos
Generan y publican el primer tweet nuevo encontrado en Hacker News para cada tema:
```bash
python -m bots.codigo
python -m bots.teclados
```

Para más detalles sobre el bot de mejora, ver [docs/mejorar-tweet.md](docs/mejorar-tweet.md).

## Estructura de Obsidian

Los bots automáticos publican directamente en X. Obsidian se utiliza
únicamente para los borradores creados por los bots manuales:

```
Borradores/
└── *.md
```

### Flujo automático

El scheduler ejecuta los módulos de `bots/` en los horarios configurados.
Después de publicar correctamente, cada elemento se registra en SQLite para
evitar duplicados.

### Flujo manual

1. Ejecutar `bots.github_manual`.
2. Revisar el archivo generado en `Borradores/`.
3. Editarlo y publicarlo manualmente si corresponde.

> `RAILWAY_SYNC_ENABLED` permite registrar en Railway los borradores
> procesados localmente para evitar publicaciones duplicadas.
>
> Migración manual (sube el historial local a Railway):
>
> ```bash
> python scripts/sync_local_to_railway.py
> ```

## Estructura del Proyecto

```
trending2Tweet/
├── bots/
│   ├── github_manual.py    ← Bot manual para repos específicos
│   ├── github_trending.py  ← Bot automático para repos trending
│   ├── news.py             ← Bot general de noticias Hacker News
│   ├── codigo.py           ← Bot de noticias de programación
│   ├── teclados.py         ← Bot de noticias sobre teclados
│   └── mejorar_tweet.py    ← Bot para mejorar tweets manuales con IA
├── src/
│   ├── config.py           ← Configuración centralizada
│   ├── llm_client.py       ← Cliente para generar tweets con LLM
│   ├── obsidian_vault.py   ← Gestión de borradores en Obsidian
│   └── publishing.py       ← Publicación y registro compartidos
├── sources/
│   ├── github_client.py    ← Cliente de GitHub API
│   └── hacker_news_client.py ← Cliente de Hacker News
├── db/
│   └── metrics_db.py       ← Base de datos de métricas
├── prompts/
│   ├── prompt_github.txt      ← Prompt para tweets de GitHub
│   ├── prompt_news.txt        ← Prompt para tweets de noticias
│   ├── prompt_codigo.txt      ← Prompt para tweets de programación
│   ├── prompt_teclados.txt    ← Prompt para tweets de teclados
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

## Licencia

MIT
