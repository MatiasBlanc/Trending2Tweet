# 🤖 Trending2Tweet

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Obsidian](https://img.shields.io/badge/Obsidian-Local--First-7C3AED?logo=obsidian&logoColor=white)](https://obsidian.md)
[![LLM Support](https://img.shields.io/badge/LLM-OpenAI%20%7C%20DeepSeek%20%7C%20OpenRouter-orange)](https://platform.openai.com)
[![Architecture](https://img.shields.io/badge/Architecture-Human--in--the--Loop-teal)](https://github.com/MatiasBlanc/Trending2Tweet)
[![Made in Chile](https://madeinchile.tech/badge.svg)](https://madeinchile.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Tu asistente local para crear, pulir y organizar contenido técnico de alto valor para X (Twitter) directamente en tu bóveda de Obsidian.**

*Descubre tendencias en GitHub, Hacker News y Reddit, genera retos de código interactivos, edita cada nota con tu voz en Obsidian y publica con total control.*

<br/>

<details>
  <summary>🇺🇸 <b>Click here to read in English / Read in English</b></summary>
  <br/>

  **Trending2Tweet** is a local-first CLI and TUI assistant that finds trending tech topics across GitHub, Hacker News, and Reddit, crafting high-impact tweets, quizzes, and threads directly into your Obsidian vault with LLMs. 100% private, human-in-the-loop, and zero cloud overhead.

  ### 🎯 Key Highlights:
  - 🔒 **100% Local & Private:** No external databases. Drafts live in local Markdown notes; deduplication history in SQLite (`metrics.db`).
  - 📝 **Obsidian-Native:** Automatic tagging, Dataview-compatible YAML frontmatter, and smart auto-archiving.
  - ⚡ **Multi-LLM Support:** OpenAI, DeepSeek, OpenRouter, and local models.
</details>

</div>

---

## 🎯 La Filosofía: *Human-in-the-Loop*

La mayoría de bots de redes sociales generan spam genérico y publican sin supervisión. **Trending2Tweet** propone un enfoque distinto:

> **La IA hace el trabajo pesado de investigación y síntesis; tú mantienes el criterio, la voz y el botón de publicación.**

```text
  [ 🐙 GitHub Trending ]    [ 📰 Hacker News ]    [ ⌨️ Reddit ]    [ 🧩 Retos ]
             │                       │                 │               │
             └───────────────────────┼─────────────────┴───────────────┘
                                     ▼
                     [ 🧠 LLM (OpenAI / DeepSeek / etc.) ]
                                     ▼
                   [ 📂 Bóveda Local de Obsidian (Markdown) ]
                    Notas con frontmatter, fuentes y notas técnicas
                                     ▼
                         [ ✍️ Edición y Criterio ]
                     Revisa, personaliza o usa "Mejorar Tweet"
                                     ▼
                    [ 🚀 Publicar en X ] ──► [ 📦 Auto-Archivado ]
```

- 🔒 **100% Local y Privado:** Sin bases de datos remotas ni dependencias en la nube. Tus borradores viven en tus archivos Markdown y tu historial antiduplicados en un SQLite local (`metrics.db`).
- 📝 **Estructurado para Obsidian:** Cada tweet se guarda en su carpeta (`github/`, `news/`, `codigo/`, `teclado/`) con metadatos YAML compatibles con Dataview.
- 🧹 **Archivado Inteligente:** Al publicar o marcar una nota con `status: published`, se traslada automáticamente a `archivados/` manteniendo tu espacio de trabajo limpio.

---

## ⚡ Inicio Rápido (3 minutos)

### 1. Clonar el repositorio y preparar el entorno

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

Copia la plantilla `.env.example`:

```bash
cp .env.example .env
```

Abre `.env` y configura tus credenciales esenciales:

```env
# Proveedor de IA (OpenAI, DeepSeek, OpenRouter, etc.)
LLM_API_KEY=tu_api_key_aqui
LLM_MODEL=gpt-4o-mini # o deepseek/deepseek-chat

# Ruta hacia tu bóveda de Obsidian
OBSIDIAN_VAULT_PATH=~/Obsidian/Twitter/bot/
```

> 💡 **Nota:** Si usas **DeepSeek**, solo cambia `LLM_BASE_URL=https://api.deepseek.com/v1` y `LLM_MODEL=deepseek-chat`.

### 3. Iniciar el panel interactivo

```bash
python main.py
```

---

## 🎮 Panel Interactivo (TUI)

Al ejecutar `python main.py` sin parámetros tendrás acceso a la consola de control interactiva:

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

## 🤖 Atajos de Terminal y CLI

Puedes invocar cualquier generador directamente desde tu terminal o integrarlo con atajos de tu sistema:

| Acción | Comando CLI directo | Invocación como módulo |
|---|---|---|
| **GitHub Trending** | `python main.py github [cantidad]` | `python -m bots.github_trending [cantidad]` |
| **GitHub Repo Concreto** | `python main.py manual usuario/repo` | `python -m bots.github_manual usuario/repo` |
| **Tech News (HN)** | `python main.py news [cantidad]` | `python -m bots.news [cantidad]` |
| **Code News** | `python main.py codigo [cantidad]` | `python -m bots.codigo [cantidad]` |
| **Retos de Código** | `python main.py retos [lenguaje] [cant] [nivel]` | `python -m bots.retos [lenguaje] [cant] [nivel]` |
| **Teclados (Reddit)** | `python main.py teclado [cantidad]` | `python -m bots.teclados [cantidad]` |
| **Mejorar Tweet** | `python main.py mejorar` | `python -m bots.mejorar_tweet` |
| **Archivar Publicados** | `python main.py archivar` | `python -m bots.archivar` |
| **Ver Estadísticas** | `python main.py stats` | `python -m src.obsidian_vault` |

### Ejemplos útiles:

```bash
# Generar 2 propuestas de repositorios trending en GitHub
python main.py github 2

# Analizar a fondo un proyecto específico leyendo su README y estrellas
python main.py manual facebook/react

# Generar un reto/quiz técnico de TypeScript en dificultad media
python main.py retos typescript 1 medio

# Generar un borrador de cada categoría en lote
./scripts/sync_and_tui.sh
```

---

## 📁 Organización en Obsidian

Los borradores se guardan directamente como notas Markdown limpias dentro de tu bóveda:

```text
~/Obsidian/Twitter/bot/
├── github/      ← Repos trending y proyectos analizados
├── news/        ← Noticias y debates tech de Hacker News
├── codigo/      ← Tips de programación y retos técnicos
├── teclado/     ← Builds, switches y periféricos mecánicos
└── archivados/  ← Notas publicadas organizadas por categoría
    ├── github/
    ├── news/
    ├── codigo/
    └── teclado/
```

### Anatomía de un borrador generado:

```markdown
---
status: draft
category: github
source: github_trending
titulo: "shadcn/ui"
url: "https://github.com/shadcn-ui/ui"
repo_stars: 72000
created_at: 2026-09-01T15:00:00
---

Hermoso componente CLI que no instalas como dependencia, sino que copias
el código directamente en tu proyecto.

¿Por qué este enfoque está ganando?
→ Control total sobre el estilo y accesibilidad
→ Cero sorpresas en actualizaciones de paquetes npm

---
## Notas
- 72.000 estrellas en GitHub.
- Ideal para acompañar con un hilo comparativo sobre librerías de componentes tradicionales.
```

---

## 📦 Sistema de Archivado Automático

Cuando publiques un tweet en X, simplemente actualiza el frontmatter en tu nota:

```yaml
---
status: published
---
```
*(o añade `published: true`)*.

El sistema detectará automáticamente el cambio y moverá la nota a la carpeta `archivados/<categoria>/`:
- Se ejecuta en segundo plano al generar nuevo contenido.
- O manualmente en cualquier momento con `python main.py archivar`.

---

## ⚙️ Referencia de Variables (`.env`)

| Variable | Requerida | Por Defecto | Descripción |
|---|:---:|:---:|---|
| `LLM_API_KEY` | **Sí** | — | Clave de API de tu proveedor de LLM. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Endpoint compatible con OpenAI (DeepSeek, OpenRouter, Azure). |
| `LLM_MODEL` | No | `gpt-4o-mini` | Modelo a utilizar (ej. `gpt-4o-mini`, `deepseek-chat`). |
| `OBSIDIAN_VAULT_PATH` | No | `~/Obsidian/Twitter/bot/` | Ruta a la carpeta de borradores en tu máquina. |
| `GITHUB_TOKEN` | No | — | Token personal de GitHub (evita rate limits en la API). |
| `FORCE_280_CHAR_TWEET` | No | `false` | `true` limita a 280 caracteres; `false` permite formato largo (X Premium). |
| `TWITTER_API_*` | No | — | Credenciales de X API v2 (solo si deseas publicar desde el menú opción 9). |

---

## 🔒 Privacidad y Almacenamiento Local

- **Tus notas no salen de tu máquina:** Todo se guarda en archivos Markdown estándar legibles.
- **Sin telemetría ni servidores intermedios:** No hay tracking ni analíticas ocultas.
- **Historial antifraude:** Se guarda únicamente un identificador hash en un archivo SQLite local (`metrics.db`) para evitar sugerirte dos veces la misma noticia o repositorio.

---

## 📜 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
