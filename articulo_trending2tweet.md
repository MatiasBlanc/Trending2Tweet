# Trending2Tweet: Arquitectura de un bot que transforma código en contenido viral

Publicar contenido técnico en X (Twitter) todos los días es un trabajo que consume más tiempo del que admite. No por escribir — eso es lo fácil — sino por **encontrar qué escribir**, filtrar lo que ya publicaste, adaptar el tono al algoritmo, y medir si funcionó.

Diseñé **Trending2Tweet** para que ese trabajo desaparezca.

El bot escanea repositorios trending de GitHub y noticias de Hacker News, genera tweets optimizados para engagement con un LLM, los publica automáticamente con tarjetas visuales, y luego mide el rendimiento real de cada publicación. Todo sin intervención manual.

Pero este artículo no es sobre qué hace. Es sobre **cómo está construido por dentro** — y por qué cada decisión técnica existe por una razón concreta.

---

## 1. El Stack: mínimo por diseño

```
Python 3.10+
openai        → cliente LLM universal (cualquier proveedor compatible)
requests      → llamadas a GitHub y Hacker News APIs
tweepy        → publicación en X (API v2 + v1.1 para media)
Pillow        → generación de tarjetas visuales
sqlite3       → estado, métricas e historial (incluido en Python)
```

**No hay framework. No hay base de datos externa. No hay cola de mensajes.**

Esta es una decisión deliberada. El bot corre en un solo proceso, en un solo archivo ejecutable, en un solo servidor. Cada dependencia que no está ahí es una que no puede romperse a las 3 AM.

La única abstracción real es `config.py`, que centraliza toda la configuración desde variables de entorno:

```python
# config.py — todo sale de .env, nada está hardcodeado
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
FORCE_280_CHAR_TWEET: bool = os.getenv("FORCE_280_CHAR_TWEET", "true").lower() == "true"
NEWS_MIN_SCORE: int = int(os.getenv("NEWS_MIN_SCORE", "50"))
```

Ese `LLM_BASE_URL` es la clave. El bot usa el SDK de OpenAI, pero al poder cambiar la URL base, apuntas a cualquier proveedor compatible sin tocar una línea de código:

| Proveedor | BASE_URL | Caso de uso |
|-----------|----------|-------------|
| OpenAI | `https://api.openai.com/v1` | Máxima calidad |
| Groq | `https://api.groq.com/openai/v1` | Ultra rápido, barato |
| Ollama | `http://localhost:11434/v1` | Gratis, local, privado |
| Xiaomi MiMo | URL del endpoint corporativo | Entornos internos |

**Un cambio en `.env` cambia el motor de IA.** Sin refactor, sin deploy, sin dependencias nuevas.

---

## 2. El flujo de 5 pasos (y por qué el orden importa)

El script principal orquesta un pipeline que no desperdicia recursos. Cada paso alimenta al siguiente, y cualquiera puede abortar limpiamente:

```
GitHub/HN API  →  Filtro de estado  →  LLM  →  Tarjeta visual  →  Twitter
      ↓                ↓                ↓            ↓              ↓
  10 repos         8 ya vistos      2 nuevos     1 tweet + img    Publicado
```

### Paso 1: Descubrimiento

```python
# sources/github_client.py
def get_trending_repos(limit: int = 10) -> List[dict]:
    since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    params = {
        "q": f"created:>{since}",
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 100),
    }
    resp = requests.get(f"{GITHUB_API}/search/repositories", params=params, headers=headers)
    # ...
```

La query `created:>2025-06-27 sort:stars` devuelve los repos más estrellados del último mes. No los más recientes — los más **relevantes**. Un repo con 5000 stars en 2 semanas vale más que uno con 10 stars creado ayer.

Para Hacker News el criterio es diferente: se usa el score como filtro de calidad (`NEWS_MIN_SCORE=50`) para evitar ruido.

### Paso 2: Filtro de memoria

Antes de gastar un solo token del LLM, el bot consulta SQLite:

```python
# metrics_db.py
def is_processed(item_id: str) -> bool:
    cursor.execute("SELECT 1 FROM tweets WHERE item_id = ? LIMIT 1", (item_id,))
    return cursor.fetchone() is not None
```

Si el repo ya fue publicado, se descarta. Si la noticia ya se cubrió, se descarta. **Cero llamadas desperdiciadas al LLM.**

### Paso 3: Generación con el LLM

Aquí ocurre la magia. El bot descarga el README del repo (hasta 4000 caracteres), lo inyecta junto con los datos del repo, y envía todo al modelo:

```python
# main_github.py
def construir_mensaje_usuario(repo: dict) -> str:
    msg = (
        f"Repo: {repo['name']}\n"
        f"Descripción: {repo['description']}\n"
        f"Lenguaje: {repo['language']}\n"
        f"Stars: {repo['stars']}"
    )
    readme_content = repo.get("readme_content")
    if readme_content:
        msg += f"\n\n--- README del repositorio ---\n{readme_content}"
    return msg
```

Pero el prompt del sistema es donde está la ingeniería real. No es un "escribe un tweet sobre esto". Es un documento de 2000+ caracteres con reglas específicas optimizadas para el algoritmo de X:

```
LÍNEA 1 — EL GANCHO (Hook):
NUNCA empieces con el nombre del repo.
NUNCA empieces con "Un repo", "Este proyecto" o "Hoy".

CIERRE — EL DISPARADOR DE CONVERSACIÓN:
Evita cierres genéricos como "¿Qué opinan?" o "¡Increíble herramienta!"

REGLAS ABSOLUTAS:
PROHIBIDO usar: "descubre", "revolucionario", "increíble", "potente", "robusto"...
```

El prompt está diseñado para maximizar tres métricas del algoritmo de X: **dwell time** (tiempo de lectura), **bookmark rate** (guardados), y **reply velocity** (respuestas en los primeros 30 minutos).

Para noticias, el sistema es aún más sofisticado. Usa **8 estilos de gancho aleatorios** que varían el tono en cada tweet para evitar el patrón de "post automatizado":

```python
ESTILOS_GANCHO = [
    "Abre con la consecuencia más incómoda o inesperada de esta noticia para los developers...",
    "Usa el formato 'Todo lo que sabíamos sobre [X] acaba de cambiar'...",
    "Abre revelando el dato más sorprendente o contraintuitivo...",
    # ... 5 estilos más
]
```

### Paso 4: Tarjeta visual

Cada tweet se publica con una imagen de 1600×900px generada con Pillow. Sin dependencias externas, sin APIs de diseño, sin templates de Figma:

```python
# card_generator.py
def generate_github_card(repo_name, description, language, stars) -> bytes:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient(draw, W, H, GH_BG_TOP, GH_BG_BOTTOM)
    # Panel central con stats, badges, lenguaje, branding...
```

Las tarjetas usan una paleta dark mode con gradientes, grid de puntos decorativo, y pill-shaped badges para el lenguaje. GitHub tiene acento azul, Hacker News tiene acento naranja. Cada tipo de contenido tiene su propia identidad visual.

### Paso 5: Publicación y persistencia

La publicación usa Twitter API v2 para el tweet y v1.1 para subir la imagen (la API v2 aún no soporta media upload de forma nativa):

```python
# twitter_client.py
def publicar_tweet(texto, source, item_id, image_bytes) -> dict:
    media_id = subir_imagen(image_bytes) if image_bytes else None
    kwargs = {"text": texto}
    if media_id:
        kwargs["media_ids"] = [media_id]
    respuesta = client.create_tweet(**kwargs)
    registrar_tweet(tweet_id=respuesta.data["id"], ...)
    return {"id": tweet_id, "has_media": media_id is not None}
```

Después de publicar, el tweet se registra en SQLite con su fuente, prompt usado, estilo de gancho, y timestamp. **Esto es lo que alimenta el sistema de métricas.**

---

## 3. La base de datos que nadie ve (pero lo cambia todo)

El proyecto usa SQLite con dos tablas:

```sql
CREATE TABLE tweets (
    tweet_id TEXT PRIMARY KEY,
    texto TEXT NOT NULL,
    source TEXT NOT NULL,           -- github, news, github_manual
    prompt_file TEXT,               -- qué prompt se usó
    template_estilo TEXT,           -- qué estilo de gancho (noticias)
    published_at TEXT NOT NULL,
    engagement_score REAL DEFAULT 0.0,
    likes_latest INTEGER DEFAULT 0,
    retweets_latest INTEGER DEFAULT 0,
    replies_latest INTEGER DEFAULT 0,
    bookmarks_latest INTEGER DEFAULT 0
);

CREATE TABLE metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    likes INTEGER, retweets INTEGER, replies INTEGER,
    impressions INTEGER, bookmarks INTEGER
);
```

La tabla `metrics_history` guarda **snapshots temporales** de cada tweet. El sistema colecta métricas en ventanas de tiempo específicas: 30 minutos y 24 horas después de publicar. Esto permite ver la **evolución** del engagement, no solo el estado final.

El engagement score se calcula con pesos configurables:

```python
# Pesos por defecto (ajustables en .env)
ENGAGEMENT_WEIGHTS = {
    "likes": 1.0,      # engagement pasivo
    "retweets": 2.0,    # amplificación
    "replies": 3.0,     # conversación (lo que más valora el algoritmo)
    "bookmarks": 2.5,   # intención de releer
}
```

Un reply vale 3x un like. No es arbitrario: es cómo funciona el algoritmo de X. Los replies indican conversación, y la conversación es lo que distribuye el tweet.

---

## 4. El Scheduler: publicación autónoma

El bot no necesita un cron job externo. Tiene su propio scheduler en `scheduler.py` que maneja todo:

```python
HORARIOS_PUBLICACION = [
    {"hora": 9,  "script": "main_news.py",   "label": "📰 News"},
    {"hora": 12, "script": "main_github.py",  "label": "🐙 GitHub"},
]

VENTANAS_COLECTA = [
    {"minutos": 30,   "label": "T+30min"},   # engagement temprano
    {"minutos": 1440, "label": "T+24h"},      # rendimiento del primer día
]
```

El scheduler corre en loop, verifica cada minuto si es hora de publicar, y cada 5 minutos si hay tweets pendientes de colectar métricas. Maneja timezone configurable (`PUBLISH_TIMEZONE_OFFSET`), rate limits de Twitter (espera 15 minutos si recibe 429), y se cierra limpiamente con SIGTERM.

**Para deployment en producción**, el proyecto soporta Railway, Heroku, y VPS con systemd. El `Procfile` de Heroku es un solo worker:

```
worker: python scheduler.py
```

---

## 5. Dashboard y TUI: métricas sin salir de la terminal

El proyecto incluye una TUI interactiva construida con Textual (el framework TUI de Rich):

```
┌─────────────────────────────────────────────┐
│  📊 Trending2Tweet Dashboard                │
├─────────────────────────────────────────────┤
│  Total tweets: 47                           │
│  Total likes: 1,234 | RTs: 567 | Replies: 89│
│  Engagement promedio: 23.4                  │
│  Mejor tweet: 892 pts (GitHub, 2025-07-15)  │
├─────────────────────────────────────────────┤
│  [1] Por fecha  [2] Por likes  [3] Por score│
│  [f] Filtrar fuente  [r] Refrescar          │
└─────────────────────────────────────────────┘
```

Con `1/2/3` ordenas por fecha, likes o engagement. Con `f` filtras por fuente. Con `Enter` ves el detalle de un tweet con su historial de métricas. Todo sin abrir un navegador.

---

## 6. Lo que no hicimos (y por qué)

**No publicamos directamente desde el bot.** El flujo genera el tweet, lo guarda en `/tweets`, y lo publica en X. Pero el archivo `.txt` se conserva como backup con la URL del repo para agregarla como comentario. Esto da un control total al usuario.

**No usamos frameworks como LangChain o CrewAI.** El flujo es secuencial y determinista. Un framework hubiera añadido 15 dependencias para resolver un problema que `openai.Client()` resuelve en 3 líneas.

**No usamos bases de datos externas.** SQLite es suficiente para miles de tweets y cientos de snapshots de métricas. Si necesitas PostgreSQL, probablemente estás escalando más allá de lo que un bot de Twitter necesita.

**No hardcodeamos el proveedor de IA.** La arquitectura con `LLM_BASE_URL` permite cambiar de OpenAI a Groq a Ollama sin modificar el código. Hoy usas GPT-4o-mini, mañana cambias a un modelo más barato, y el bot sigue funcionando.

---

## Resultado

El bot publica 2 tweets diarios (uno de noticias por la mañana, uno de GitHub al mediodía), genera tarjetas visuales, mide el engagement real, y se ejecuta sin supervisión en Railway.

**El código está en [GitHub](https://github.com/trending2tweet).** El README incluye instrucciones para Railway, Heroku, y VPS con systemd.

Si llegaste hasta aquí, probablemente te interese una cosa: **la arquitectura del prompt**. Los prompts en `/prompts/` son donde está el verdadero valor del proyecto. El código es el vehículo; el prompt es el conductor.

---

*¿Ya estás automatizando tu contenido técnico? ¿Qué stack usas?*
