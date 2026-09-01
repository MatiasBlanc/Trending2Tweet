# 🤖 Trending2Tweet

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Obsidian](https://img.shields.io/badge/Obsidian-Ready-7C3AED?logo=obsidian&logoColor=white)](https://obsidian.md)
[![LLM Support](https://img.shields.io/badge/LLM-OpenAI%20%7C%20DeepSeek%20%7C%20OpenRouter-orange)](https://platform.openai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Tu asistente local para crear, pulir y gestionar contenido técnico para X (Twitter) directamente en tu bóveda de Obsidian.**

*Genera tweets y retos de alto valor a partir de GitHub Trending, Hacker News y Reddit, edítalos con tranquilidad en Obsidian y publícalos cuando tú decidas.*

</div>

---

## 💡 ¿Por qué Trending2Tweet?

- **100% Manual y Bajo tu Control:** Sin bots autónomos publicando cosas sin revisar en tu cuenta. Tú eliges qué generar y cuándo publicar.
- **Integrado con Obsidian:** Guarda cada tweet como una nota Markdown con metadatos estructurados (YAML frontmatter), enlaces a las fuentes y notas de contexto.
- **Múltiples Fuentes de Inspiración:** GitHub Trending, repositorios específicos, debates de Hacker News, comunidades de periféricos y quizzes de código interactivos.
- **Optimización con IA:** Herramienta integrada para mejorar tweets existentes y adaptarlos a formatos virales o hilos.
- **Archivado Inteligente:** Mueve automáticamente a `archivados/` los tweets que marques como `status: published`.

---

## ⚡ Inicio Rápido (3 minutos)

### 1. Clonar el repositorio y crear entorno virtual

```bash
git clone https://github.com/MatiasBlanc/Trending2Tweet.git
cd Trending2Tweet

# Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia la plantilla de configuración:

```bash
cp .env.example .env
```

Abre `.env` y añade tu clave de IA (OpenAI, DeepSeek o compatible) y la ruta a tu bóveda de Obsidian:

```env
# Mínimo imprescindible para funcionar:
LLM_API_KEY=tu_api_key_aqui
OBSIDIAN_VAULT_PATH=~/Obsidian/Twitter/bot/
```

> 💡 **Nota:** Si no tienes OpenAI, puedes usar **DeepSeek** o cualquier proveedor compatible configurando `LLM_BASE_URL` y `LLM_MODEL`.

### 3. ¡Listo! Ejecutar el panel interactivo

```bash
python main.py
```

---

## 🎮 Panel Interactivo

Al ejecutar `python main.py` sin argumentos verás el menú principal interactivo:

```text
╭──────────────────────────────────────────────────────────────────────────╮
│  🤖  TRENDING2TWEET                                                      │
│  Panel de creación y revisión de contenido para Obsidian                 │
│  📂 Bóveda: ~/Obsidian/Twitter/bot                                       │
╰──────────────────────────────────────────────────────────────────────────╯

  ✦ CREAR CONTENIDO
   1. 🐙 GitHub Trending     repositorios nuevos con más actividad
   2. 🐙 GitHub Manual       analizar un repositorio concreto
   3. 📰 Tech News           noticias tecnológicas de Hacker News
   4. 💻 Code News           historias y aprendizajes de programación
   5. 🧩 Retos de Código     desafíos por lenguaje y dificultad
   6. ⌨️  Teclados           publicaciones de periféricos desde Reddit

  ✦ REVISAR Y GESTIONAR
   7. ✨ Mejorar Tweet       pulir un tweet de la bóveda con IA
   8. 📦 Archivar            mover publicaciones marcadas como publicadas
   9. 🚀 Publicar en X       publicar un borrador después de revisarlo
  10. 📊 Estadísticas        ver el estado de la bóveda

   0. 👋 Salir
```

---

## 🤖 Uso Directo por CLI

Si prefieres ejecutar comandos directos o automatizar con atajos de terminal, puedes pasar los argumentos a `main.py` o invocar cada módulo:

| Acción | Comando CLI directo | Comando por módulo |
|---|---|---|
| **GitHub Trending** | `python main.py github [cantidad]` | `python -m bots.github_trending [cantidad]` |
| **GitHub Repo Específico** | `python main.py manual usuario/repo` | `python -m bots.github_manual usuario/repo` |
| **Tech News (HN)** | `python main.py news [cantidad]` | `python -m bots.news [cantidad]` |
| **Code News** | `python main.py codigo [cantidad]` | `python -m bots.codigo [cantidad]` |
| **Retos de Código** | `python main.py retos [lenguaje] [cantidad] [dificultad]` | `python -m bots.retos [lenguaje] [cantidad] [dificultad]` |
| **Teclados (Reddit)** | `python main.py teclado [cantidad]` | `python -m bots.teclados [cantidad]` |
| **Mejorar Tweet** | `python main.py mejorar` | `python -m bots.mejorar_tweet` |
| **Archivar Publicados** | `python main.py archivar` | `python -m bots.archivar` |
| **Ver Estadísticas** | `python main.py stats` | — |

### Ejemplos de uso rápido:

```bash
# Generar 2 tweets de repos trending en GitHub
python main.py github 2

# Analizar un repositorio en particular
python main.py manual facebook/react

# Generar un reto de Python en nivel difícil
python main.py retos python 1 dificil

# Ejecutar una pasada en lote de todas las categorías
./scripts/sync_and_tui.sh
```

---

## 📁 Estructura en Obsidian

Los borradores se guardan directamente como archivos Markdown legibles en tu bóveda:

```text
~/Obsidian/Twitter/bot/
├── github/      ← Repos trending y proyectos analizados
├── news/        ← Noticias y debates de tecnología (Hacker News)
├── codigo/      ← Tips de programación y retos técnicos
├── teclado/     ← Builds, switches y periféricos (Reddit)
└── archivados/  ← Tweets que ya fueron publicados en X
    ├── github/
    ├── news/
    ├── codigo/
    └── teclado/
```

### Formato de cada borrador:

Cada nota incluye Frontmatter YAML compatible con Dataview y plugins de Obsidian:

```markdown
---
status: draft
category: github
source: github_trending
titulo: "Repo Increíble"
url: "https://github.com/..."
created_at: 2026-09-01T15:00:00
---

Este es el texto del tweet generado por la IA listo para ser revisado y compartido.

---
## Notas
- Contexto de la fuente, estrellas o debates relevantes.
```

---

## 📦 Flujo de Archivado Automático

Cuando publiques un tweet en X, simplemente cambia el frontmatter en tu nota de Obsidian:

```yaml
---
status: published
---
```
*(o añade `published: true`)*.

El sistema detectará el cambio y moverá la nota automáticamente a la subcarpeta `archivados/<categoria>/` correspondiente:
- Se ejecuta de fondo cada vez que generas nuevo contenido.
- O manualmente con `python main.py archivar`.

---

## ⚙️ Configuración (`.env`)

| Variable | Requerida | Por Defecto | Descripción |
|---|:---:|:---:|---|
| `LLM_API_KEY` | **Sí** | — | Clave de API de tu proveedor de LLM. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Endpoint compatible con OpenAI (DeepSeek, OpenRouter, Azure). |
| `LLM_MODEL` | No | `gpt-4o-mini` | Modelo a utilizar (ej. `gpt-4o-mini`, `deepseek-chat`). |
| `OBSIDIAN_VAULT_PATH` | No | `~/Obsidian/Twitter/bot/` | Ruta local donde se almacenarán las carpetas de borradores. |
| `GITHUB_TOKEN` | No | — | Token de GitHub (evita límites de tasa al buscar repositorios). |
| `FORCE_280_CHAR_TWEET` | No | `false` | `true` para limitar tweets a 280 caracteres; `false` para tweets largos de X Premium. |
| `TWITTER_API_*` | No | — | Credenciales de X v2 (solo necesarias si quieres publicar desde el menú opción 9). |

---

## 🔒 Privacidad y Almacenamiento Local

- **Tus notas son tuyas:** Todo se almacena en archivos Markdown estándar en tu sistema de archivos.
- **Historial antifraude/antiduplicados:** Se registra únicamente un hash/ID local en un archivo SQLite (`metrics.db`) para no repetirte los mismos temas o repositorios.
- **Sin telemetría ni servidores intermedios:** La aplicación solo se comunica con la API del LLM que configures y las APIs públicas de las fuentes (GitHub, Hacker News, Reddit).

---

## 📜 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.
