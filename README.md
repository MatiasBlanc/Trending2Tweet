# 🐦 Trending2Tweet - Flujo Manual con Obsidian

Sistema semi-automático para generar tweets sobre noticias y repos de GitHub, con revisión y publicación manual.

## 📁 Estructura en Obsidian

```
obsidian-vault/
├── T2T/                          # Tweets automáticos
│   ├── borradores/               # Generados por el bot (pendientes)
│   ├── listos/                   # Editados y listos para publicar
│   └── publicados/               # Ya en Twitter
├── manual/                       # Tweets manuales
│   ├── borradores/
│   ├── listos/
│   └── publicados/
├── Templates/                    # Templates de gancho
├── Calendar/                     # Calendario editorial
├── Reports/                      # Reportes de engagement
└── analytics/                    # CSVs de Twitter Analytics
```

## 🚀 Flujo de Trabajo

### 1. Generar Borradores

**GitHub Trending (automático, 1x/día):**
```bash
python main_github.py
```

**GitHub Manual (repo específico):**
```bash
python main_github_manual.py usuario/repo
python main_github_manual.py cheahjs/free-llm-api-resources
```

**Noticias (automático):**
```bash
python main_news.py
```

### 2. Revisar en Obsidian

1. Abre la bóveda en `/home/mblanc/workspaces/twitter/obsidian-vault`
2. Revisa los borradores en `T2T/borradores/`
3. Edita el tweet, agrega tu toque personal
4. Marca el checklist de revisión

### 3. Marcar como Listo

Mueve el archivo de `borradores/` a `listos/` cuando esté listo para publicar.

O usa el script:
```bash
python obsidian_manager.py listos  # Ver tweets listos
```

### 4. Publicar en Twitter (Manual)

1. Copia el texto del tweet desde Obsidian
2. Pega en Twitter y publica
3. Copia la URL del tweet publicado
4. Registra la publicación:

```bash
python obsidian_manager.py publicar "nombre-archivo.md" "https://x.com/usuario/status/123"
```

### 5. Ver Estado

```bash
python obsidian_manager.py estado      # Resumen general
python obsidian_manager.py borradores  # Lista de borradores
python obsidian_manager.py listos      # Lista de tweets listos
```

## 📊 Analytics (Opcional)

Para que la IA aprenda de tus tweets, puedes subir CSVs de Twitter Analytics:

1. Descarga el CSV desde [analytics.twitter.com](https://analytics.twitter.com)
2. Cópialo a `obsidian-vault/analytics/`
3. O usa el script:

```bash
python obsidian_manager.py analytics ~/Downloads/analytics_2026-07.csv
```

## ⚙️ Configuración

En `.env`:
```env
# Ruta a la bóveda de Obsidian
OBSIDIAN_VAULT_PATH=/home/mblanc/workspaces/twitter/obsidian-vault

# API Keys
GITHUB_TOKEN=tu_token
LLM_API_KEY=tu_api_key
LLM_BASE_URL=https://api.xiaomi.com/v1
LLM_MODEL=mimo-v2.5-pro

# Control de tweets
FORCE_280_CHAR_TWEET=false
```

## 📝 Ejemplo de Borrador en Obsidian

```markdown
---
type: tweet
status: draft
source: github
date: 2026-07-28T14:30:00
url: https://github.com/cheahjs/free-llm-api-resources
repo: cheahjs/free-llm-api-resources
stars: 12500
---

# cheahjs/free-llm-api-resources

## Tweet

Olvídate de pagar $20/mes por la API de OpenAI. Este repo tiene TODOS los 
proveedores de LLM con tier gratuito, actualizado semanalmente.

🔥 12,500 stars | 200+ proveedores listados

## Metadata

- **Fuente**: github
- **Fecha**: 2026-07-28
- **Caracteres**: 187
- **URL**: https://github.com/cheahjs/free-llm-api-resources
- **Stars**: 12500

## Revisión

- [ ] Revisar ortografía
- [ ] Verificar datos/fuentes
- [ ] Agregar toque personal
- [ ] Verificar longitud (280 chars)
- [ ] Mover a 'listos' cuando esté listo
```

## 🎯 Ventajas de este Flujo

| Ventaja | Descripción |
|---------|-------------|
| **$0 en API** | No necesitas pagar la API de Twitter |
| **Control total** | Revisas cada tweet antes de publicar |
| **Calidad** | Puedes editar y mejorar cada tweet |
| **Timing** | Publicas cuando tu audiencia está activa |
| **Aprendizaje** | Los analytics ayudan a mejorar |
| **Organización** | Todo centralizado en Obsidian |

## 📂 Archivos del Proyecto

```
trending2Tweet/
├── main_github.py          # Bot GitHub trending → borradores
├── main_github_manual.py   # Bot GitHub manual → borradores
├── main_news.py            # Bot noticias → borradores
├── obsidian_vault.py       # Módulo de gestión en Obsidian
├── obsidian_manager.py     # CLI para gestionar tweets
├── config.py               # Configuración
├── llm_client.py           # Cliente del LLM
├── sources/                # Fuentes de datos
│   ├── github_client.py
│   └── news_client.py
└── prompts/                # Prompts para el LLM
    └── prompt_github.txt
```
