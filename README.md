# Trending2Tweet

Bot que descubre repositorios trending en GitHub y genera tweets técnicos con IA para publicar manualmente en X (Twitter).

## Requisitos

- Python 3.10+
- Cuentas con acceso a la API de GitHub y a un proveedor LLM compatible con OpenAI

## Dependencias

```bash
pip install requests openai python-dotenv
```

## Configuración

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```dotenv
# GitHub API (https://github.com/settings/tokens)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# LLM API
LLM_API_KEY=tu_api_key
LLM_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
LLM_MODEL=mimo-v2.5-pro

# Parámetros del LLM (opcionales)
LLM_MAX_TOKENS=1024      # Máximo de tokens en la respuesta
LLM_TEMPERATURE=0.2      # Creatividad: 0.0=determinista, 1.0=creativo

# Ruta al archivo de estado (opcional, por defecto state.json)
STATE_FILE=state.json

# Limitar tweets a 280 caracteres (opcional)
# true  = modo estándar (280 chars máx)
# false = tweets largos (requiere X Premium)
FORCE_280_CHAR_TWEET=true
```

### Obtener credenciales

| Servicio   | Dónde obtenerlas                                                                             | Permisos necesarios     |
| ---------- | -------------------------------------------------------------------------------------------- | ----------------------- |
| **GitHub** | [Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens) | `public_repo` (lectura) |
| **LLM**    | Panel de tu proveedor (OpenAI, Groq, Xiaomi MiMo, etc.)                                     | Acceso a chat completions |

### Proveedores LLM

El bot usa el SDK de OpenAI, compatible con cualquier proveedor que exponga la misma interfaz:

```dotenv
# Xiaomi MiMo
LLM_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
LLM_MODEL=mimo-v2.5-pro

# Groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b

# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Ollama (local)
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=llama3.1
```

## Estructura del proyecto

```
.
├── .env              # Credenciales (no versionar)
├── state.json        # IDs de repos ya publicados (se gestiona solo)
├── tweets/           # Carpeta con los tweets generados
├── config.py         # Carga y exporta variables de entorno
├── github_client.py  # Busca el repo con más stars del último mes
├── llm_client.py     # Genera el texto del tweet con un LLM
├── state_manager.py  # Persistencia en state.json
├── menu.py           # Menú interactivo y gestión de historial
└── main.py           # Orquestador principal
```

## Ejecución

```bash
python main.py
```

Al ejecutar, aparece un menú interactivo:

```
==================================================
         Trending2Tweet
==================================================
  1. Iniciar a twittear
  2. Gestionar historial
  0. Salir
==================================================
```

### Opción 1: Iniciar a twittear

1. **Descubrimiento** — Consulta la GitHub Search API para obtener los 10 repos creados en los últimos 30 días ordenados por estrellas.
2. **Filtrado** — Descarta repos ya publicados comparando con `state.json`.
3. **Interacción** — Muestra cada repo y pregunta al usuario si quiere generar un tweet para él.
4. **Generación** — Envía los datos del repo al LLM para redactar un tweet técnico, adaptando la longitud según la configuración.
5. **Guardado** — Guarda el tweet en un archivo `.txt` dentro de la carpeta `tweets/` con formato `tweet_REPO_TIMESTAMP.txt`.
6. **Persistencia** — Guarda el ID del repo en `state.json` para no repetirlo.
7. **Continuar** — Pregunta si quiere buscar el siguiente repositorio en la lista.

El usuario copia el contenido del archivo `.txt` y lo publica manualmente en X.

### Opción 2: Gestionar historial

Permite:
- Ver repos procesados en `state.json`
- Ver archivos de tweets guardados
- Eliminar repos específicos del historial
- Eliminar archivos de tweets específicos
- Limpiar todo el historial (state.json + carpeta tweets/)

## Ejecución periódica (cron)

Para ejecutar el bot una vez al día a las 9:00:

```bash
crontab -e
```

```cron
0 9 * * * cd /ruta/al/proyecto && /usr/bin/python3 main.py >> bot.log 2>&1
```

## Configuración de longitud de tweets

| `FORCE_280_CHAR_TWEET` | Comportamiento                                              | Requisito      |
| ----------------------- | ----------------------------------------------------------- | -------------- |
| `true`                  | La IA genera tweets de máximo 280 caracteres                | Cualquier plan |
| `false`                 | La IA genera tweets largos con más detalle técnico          | X Premium      |

## Manejo de errores

| Escenario              | Comportamiento                             |
| ---------------------- | ------------------------------------------ |
| Error en la API de LLM | Mensaje de error y salida limpia           |
| Sin repos nuevos       | Mensaje informativo y salida sin errores   |
| Repo ya publicado      | Se omite y finaliza sin acción             |

## Notas

- El archivo `state.json` se crea automáticamente en la primera ejecución.
- No incluir `state.json` ni `.env` en control de versiones.
- Los tweets se guardan en la carpeta `tweets/` con el formato `tweet_REPO_TIMESTAMP.txt`.
- La carpeta `tweets/` se crea automáticamente si no existe.
