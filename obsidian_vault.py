"""Módulo para guardar tweets en bóveda de Obsidian.

Genera archivos Markdown con frontmatter de Obsidian
para crear una base de conocimiento de contenido.

Funcionalidades:
- Guardar tweets con metadata completa
- Actualizar métricas automáticamente
- Templates de gancho reutilizables
- Calendario editorial
- Reportes semanales de engagement
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import config

# Nombre de las carpetas dentro de la bóveda
TWEETS_FOLDER = "Tweets"
TEMPLATES_FOLDER = "Templates"
CALENDAR_FOLDER = "Calendar"
REPORTS_FOLDER = "Reports"


def _sanitize_filename(texto: str, max_length: int = 50) -> str:
    """Sanitiza un texto para usar como nombre de archivo.

    Args:
        texto: Texto a sanitizar.
        max_length: Longitud máxima del nombre.

    Returns:
        Nombre de archivo seguro.
    """
    # Convertir a minúsculas
    texto = texto.lower()
    # Reemplazar caracteres especiales por guiones
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    # Reemplazar espacios por guiones
    texto = re.sub(r'\s+', '-', texto.strip())
    # Eliminar guiones múltiples
    texto = re.sub(r'-+', '-', texto)
    # Truncar
    return texto[:max_length].rstrip('-')


def _build_frontmatter(
    tweet_id: str,
    source: str,
    item_id: Optional[str],
    published_at: str,
    prompt_file: Optional[str],
    template_estilo: Optional[str],
    url: Optional[str] = None,
) -> str:
    """Construye el frontmatter de Obsidian.

    Args:
        tweet_id: ID del tweet en Twitter.
        source: Fuente del tweet (news, github, github_manual).
        item_id: ID del item procesado.
        published_at: Fecha de publicación ISO.
        prompt_file: Ruta del prompt usado.
        template_estilo: Estilo de gancho usado.
        url: URL de la fuente original.

    Returns:
        String con el frontmatter YAML.
    """
    lines = [
        "---",
        f"id: {tweet_id}",
        f"date: {published_at}",
        f"source: {source}",
    ]

    if item_id:
        lines.append(f"item_id: {item_id}")
    
    if url:
        lines.append(f"url: {url}")
    
    if prompt_file:
        lines.append(f"prompt_file: {prompt_file}")
    
    if template_estilo:
        # Truncar estilo para legibilidad
        estilo_corto = template_estilo[:80] + "..." if len(template_estilo) > 80 else template_estilo
        lines.append(f"estilo_gancho: \"{estilo_corto}\"")
    
    lines.append("status: published")
    lines.append("engagement_score: 0")
    lines.append("---")
    
    return "\n".join(lines)


def guardar_tweet_en_vault(
    tweet_id: str,
    texto: str,
    source: str,
    item_id: Optional[str] = None,
    published_at: Optional[str] = None,
    prompt_file: Optional[str] = None,
    template_estilo: Optional[str] = None,
    url: Optional[str] = None,
    title: Optional[str] = None,
) -> Optional[str]:
    """Guarda un tweet como archivo Markdown en la bóveda de Obsidian.

    Args:
        tweet_id: ID del tweet en Twitter.
        texto: Contenido del tweet.
        source: Fuente (news, github, github_manual).
        item_id: ID del item procesado.
        published_at: Fecha de publicación (ISO string).
        prompt_file: Ruta del prompt usado.
        template_estilo: Estilo de gancho usado.
        url: URL de la fuente original.
        title: Título del tweet (para el nombre del archivo).

    Returns:
        Ruta del archivo creado, o None si no se pudo guardar.
    """
    # Verificar que la bóveda esté configurada
    if not config.OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    
    # Verificar que la bóveda existe
    if not vault_path.exists():
        print(f"  ⚠️ Bóveda de Obsidian no encontrada: {vault_path}")
        return None
    
    # Crear carpeta de tweets si no existe
    tweets_dir = vault_path / TWEETS_FOLDER / source
    tweets_dir.mkdir(parents=True, exist_ok=True)
    
    # Fecha de publicación
    if not published_at:
        published_at = datetime.now().isoformat()
    
    # Generar nombre de archivo
    fecha = datetime.fromisoformat(published_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    
    if title:
        safe_title = _sanitize_filename(title)
    else:
        # Usar las primeras palabras del tweet
        safe_title = _sanitize_filename(texto[:50])
    
    filename = f"{fecha}_{safe_title}.md"
    filepath = tweets_dir / filename
    
    # Si ya existe, agregar sufijo
    counter = 1
    while filepath.exists():
        filepath = tweets_dir / f"{fecha}_{safe_title}_{counter}.md"
        counter += 1
    
    # Construir contenido Markdown
    frontmatter = _build_frontmatter(
        tweet_id=tweet_id,
        source=source,
        item_id=item_id,
        published_at=published_at,
        prompt_file=prompt_file,
        template_estilo=template_estilo,
        url=url,
    )
    
    # Separar el tweet en secciones
    contenido = f"{frontmatter}\n\n"
    contenido += f"# {title or 'Tweet'}\n\n"
    contenido += "## Tweet\n\n"
    contenido += f"{texto}\n\n"
    
    if url:
        contenido += "## Fuente\n\n"
        contenido += f"- URL: {url}\n"
        if item_id:
            contenido += f"- ID: {item_id}\n"
        contenido += "\n"
    
    contenido += "## Metadata\n\n"
    contenido += f"- **Publicado**: {published_at}\n"
    contenido += f"- **Fuente**: {source}\n"
    contenido += f"- **Tweet ID**: [{tweet_id}](https://twitter.com/i/status/{tweet_id})\n"
    
    if template_estilo:
        contenido += f"\n## Estilo de Gancho\n\n"
        contenido += f"> {template_estilo}\n\n"
    
    contenido += "## Métricas\n\n"
    contenido += "*Las métricas se actualizarán automáticamente...*\n\n"
    contenido += "- ❤️ Likes: 0\n"
    contenido += "- 🔁 Retweets: 0\n"
    contenido += "- 💬 Replies: 0\n"
    contenido += "- 👁 Impressions: 0\n"
    
    # Escribir archivo
    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📝 Guardado en Obsidian: {filepath.relative_to(vault_path)}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error guardando en Obsidian: {e}")
        return None


def actualizar_metricas_en_vault(
    tweet_id: str,
    likes: int,
    retweets: int,
    replies: int,
    impressions: int,
    bookmarks: int = 0,
) -> bool:
    """Actualiza las métricas de un tweet en la bóveda de Obsidian.

    Busca el archivo por tweet_id en el frontmatter y actualiza
    la sección de métricas.

    Args:
        tweet_id: ID del tweet.
        likes: Número de likes.
        retweets: Número de retweets.
        replies: Número de replies.
        impressions: Número de impresiones.
        bookmarks: Número de bookmarks.

    Returns:
        True si se actualizó correctamente.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return False
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    
    if not vault_path.exists():
        return False
    
    # Buscar archivos que contengan el tweet_id
    tweets_dir = vault_path / TWEETS_FOLDER
    
    if not tweets_dir.exists():
        return False
    
    # Buscar en todos los archivos .md
    for md_file in tweets_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            
            # Verificar si este archivo contiene el tweet_id
            if f"id: {tweet_id}" not in content:
                continue
            
            # Actualizar sección de métricas
            metricas_nuevas = (
                "## Métricas\n\n"
                f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
                f"- ❤️ Likes: {likes}\n"
                f"- 🔁 Retweets: {retweets}\n"
                f"- 💬 Replies: {replies}\n"
                f"- 👁 Impressions: {impressions}\n"
                f"- 🔖 Bookmarks: {bookmarks}\n"
            )
            
            # Reemplazar sección de métricas usando regex
            patron = r"## Métricas\n\n.*?(?=\n## |\Z)"
            contenido_nuevo = re.sub(
                patron,
                metricas_nuevas,
                content,
                flags=re.DOTALL
            )
            
            # Actualizar engagement_score en frontmatter
            engagement_score = likes + (retweets * 2) + (replies * 3) + (bookmarks * 2.5)
            contenido_nuevo = re.sub(
                r"engagement_score: \d+",
                f"engagement_score: {engagement_score}",
                contenido_nuevo
            )
            
            md_file.write_text(contenido_nuevo, encoding="utf-8")
            return True
            
        except Exception as e:
            print(f"  ⚠️ Error actualizando {md_file}: {e}")
            continue
    
    return False


def listar_tweets_en_vault(source: Optional[str] = None) -> list[dict]:
    """Lista todos los tweets guardados en la bóveda.

    Args:
        source: Filtrar por fuente (opcional).

    Returns:
        Lista de diccionarios con información de cada tweet.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return []
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    tweets_dir = vault_path / TWEETS_FOLDER
    
    if not tweets_dir.exists():
        return []
    
    tweets = []
    
    for md_file in tweets_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            
            # Extraer frontmatter
            if not content.startswith("---"):
                continue
            
            end_idx = content.find("---", 3)
            if end_idx == -1:
                continue
            
            frontmatter = content[3:end_idx].strip()
            
            # Parsear campos básicos
            tweet_info = {"file": str(md_file)}
            
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    tweet_info[key.strip()] = value.strip().strip('"')
            
            # Filtrar por source si se especifica
            if source and tweet_info.get("source") != source:
                continue
            
            tweets.append(tweet_info)
            
        except Exception:
            continue
    
    return tweets


# ── Templates de Gancho ───────────────────────────────────────


def guardar_template(
    nombre: str,
    estilo_gancho: str,
    estructura: str,
    ejemplo_tweet: Optional[str] = None,
    engagement_promedio: float = 0,
    usos: int = 0,
) -> Optional[str]:
    """Guarda un estilo de gancho como template reutilizable.

    Args:
        nombre: Nombre descriptivo del template.
        estilo_gancho: Descripción del estilo de gancho.
        estructura: Estructura recomendada para el tweet.
        ejemplo_tweet: Ejemplo de tweet usando este estilo.
        engagement_promedio: Engagement promedio de tweets con este estilo.
        usos: Número de veces que se ha usado este template.

    Returns:
        Ruta del archivo creado, o None si falló.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    templates_dir = vault_path / TEMPLATES_FOLDER
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitizar nombre para archivo
    safe_name = _sanitize_filename(nombre)
    filepath = templates_dir / f"{safe_name}.md"
    
    # Construir contenido
    contenido = f"""---
type: template
nombre: "{nombre}"
usos: {usos}
engagement_promedio: {engagement_promedio}
creado: {datetime.now().isoformat()}
activo: true
---

# {nombre}

## Estilo de Gancho

{estilo_gancho}

## Estructura Recomendada

{estructura}
"""
    
    if ejemplo_tweet:
        contenido += f"""
## Ejemplo

{ejemplo_tweet}
"""
    
    contenido += f"""
## Uso

Para usar este template, pasa el nombre `{nombre}` como `template_estilo` al generar un tweet.

## Estadísticas

- **Usos**: {usos}
- **Engagement promedio**: {engagement_promedio}
"""
    
    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📋 Template guardado: {filepath.name}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error guardando template: {e}")
        return None


def listar_templates() -> list[dict]:
    """Lista todos los templates disponibles.

    Returns:
        Lista de diccionarios con información de cada template.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return []
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    templates_dir = vault_path / TEMPLATES_FOLDER
    
    if not templates_dir.exists():
        return []
    
    templates = []
    
    for md_file in templates_dir.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            
            # Extraer frontmatter
            if not content.startswith("---"):
                continue
            
            end_idx = content.find("---", 3)
            if end_idx == -1:
                continue
            
            frontmatter = content[3:end_idx].strip()
            
            template_info = {"file": str(md_file)}
            
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    template_info[key.strip()] = value.strip().strip('"')
            
            templates.append(template_info)
            
        except Exception:
            continue
    
    return templates


def obtener_template(nombre: str) -> Optional[str]:
    """Obtiene el estilo de gancho de un template por nombre.

    Args:
        nombre: Nombre del template.

    Returns:
        Estilo de gancho del template, o None si no existe.
    """
    templates = listar_templates()
    
    for template in templates:
        if template.get("nombre") == nombre:
            filepath = Path(template["file"])
            content = filepath.read_text(encoding="utf-8")
            
            # Extraer sección "Estilo de Gancho"
            match = re.search(r"## Estilo de Gancho\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if match:
                return match.group(1).strip()
    
    return None


# ── Calendario Editorial ──────────────────────────────────────


def agregar_al_calendario(
    fecha: str,
    hora: str,
    tipo: str,
    tema: str,
    notas: Optional[str] = None,
) -> Optional[str]:
    """Agrega una entrada al calendario editorial.

    Args:
        fecha: Fecha en formato YYYY-MM-DD.
        hora: Hora en formato HH:MM.
        Tipo: Tipo de publicación (news, github, manual, thread).
        tema: Tema o título del tweet.
        notas: Notas adicionales.

    Returns:
        Ruta del archivo actualizado, o None si falló.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    calendar_dir = vault_path / CALENDAR_FOLDER
    calendar_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = calendar_dir / f"{fecha}.md"
    
    # Crear o agregar al archivo
    if filepath.exists():
        contenido = filepath.read_text(encoding="utf-8")
    else:
        contenido = f"---\ndate: {fecha}\ntype: calendar\n---\n\n# Calendario Editorial - {fecha}\n\n"
    
    # Agregar entrada
    entrada = f"- [ ] **{hora}** [{tipo}] {tema}"
    if notas:
        entrada += f"\n  > {notas}"
    contenido += entrada + "\n"
    
    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📅 Agregado al calendario: {fecha} {hora}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error actualizando calendario: {e}")
        return None


def obtener_calendario(semana: Optional[str] = None) -> list[dict]:
    """Obtiene las entradas del calendario editorial.

    Args:
        semana: Fecha de inicio de la semana (YYYY-MM-DD). Si es None,
                usa la semana actual.

    Returns:
        Lista de entradas del calendario.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return []
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    calendar_dir = vault_path / CALENDAR_FOLDER
    
    if not calendar_dir.exists():
        return []
    
    # Determinar rango de fechas
    if semana:
        inicio = datetime.strptime(semana, "%Y-%m-%d")
    else:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=hoy.weekday())  # Lunes
    
    fin = inicio + timedelta(days=7)
    
    entradas = []
    
    for i in range(7):
        fecha = (inicio + timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = calendar_dir / f"{fecha}.md"
        
        if not filepath.exists():
            continue
        
        try:
            content = filepath.read_text(encoding="utf-8")
            
            # Extraer entradas (líneas que empiezan con - [ ])
            for line in content.split("\n"):
                if line.strip().startswith("- ["):
                    # Parsear: - [ ] **HH:MM** [tipo] tema
                    match = re.match(
                        r"- \[.\] \*\*(.+?)\*\* \[(.+?)\] (.+)",
                        line.strip()
                    )
                    if match:
                        entradas.append({
                            "fecha": fecha,
                            "hora": match.group(1),
                            "tipo": match.group(2),
                            "tema": match.group(3),
                            "completado": "[x]" in line,
                        })
        except Exception:
            continue
    
    return sorted(entradas, key=lambda x: (x["fecha"], x["hora"]))


# ── Reportes Semanales ────────────────────────────────────────


def generar_reporte_semanal(semana: Optional[str] = None) -> Optional[str]:
    """Genera un reporte semanal de engagement.

    Args:
        semana: Fecha de inicio de la semana (YYYY-MM-DD). Si es None,
                usa la semana anterior.

    Returns:
        Ruta del archivo del reporte, o None si falló.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    reports_dir = vault_path / REPORTS_FOLDER
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Determinar rango de fechas
    if semana:
        inicio = datetime.strptime(semana, "%Y-%m-%d")
    else:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=hoy.weekday() + 7)  # Lunes pasado
    
    fin = inicio + timedelta(days=7)
    semana_str = inicio.strftime("%Y-W%W")
    
    # Obtener tweets de la semana
    tweets = listar_tweets_en_vault()
    tweets_semana = []
    
    for tweet in tweets:
        try:
            fecha_str = tweet.get("date", "")
            if not fecha_str:
                continue
            
            fecha = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
            if inicio <= fecha < fin:
                tweets_semana.append(tweet)
        except (ValueError, TypeError):
            continue
    
    # Calcular estadísticas
    total_tweets = len(tweets_semana)
    total_engagement = sum(
        float(t.get("engagement_score", 0)) for t in tweets_semana
    )
    
    # Agrupar por fuente
    por_fuente = {}
    for tweet in tweets_semana:
        fuente = tweet.get("source", "unknown")
        if fuente not in por_fuente:
            por_fuente[fuente] = {"count": 0, "engagement": 0}
        por_fuente[fuente]["count"] += 1
        por_fuente[fuente]["engagement"] += float(tweet.get("engagement_score", 0))
    
    # Encontrar mejor y peor tweet
    mejor_tweet = max(tweets_semana, key=lambda t: float(t.get("engagement_score", 0)), default=None)
    peor_tweet = min(tweets_semana, key=lambda t: float(t.get("engagement_score", 0)), default=None)
    
    # Generar reporte
    contenido = f"""---
type: report
semana: {semana_str}
genereado: {datetime.now().isoformat()}
tweets_total: {total_tweets}
engagement_total: {total_engagement}
---

# 📊 Reporte Semanal - {semana_str}

**Período**: {inicio.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}

## Resumen

| Métrica | Valor |
|---------|-------|
| Tweets publicados | {total_tweets} |
| Engagement total | {total_engagement:.1f} |
| Engagement promedio | {total_engagement / total_tweets if total_tweets > 0 else 0:.1f} |

## Por Fuente

| Fuente | Tweets | Engagement | Promedio |
|--------|--------|------------|----------|
"""
    
    for fuente, stats in por_fuente.items():
        promedio = stats["engagement"] / stats["count"] if stats["count"] > 0 else 0
        contenido += f"| {fuente} | {stats['count']} | {stats['engagement']:.1f} | {promedio:.1f} |\n"
    
    contenido += "\n## Mejores Tweets\n\n"
    
    if mejor_tweet:
        contenido += f"""### 🏆 Mejor Tweet

- **Fuente**: {mejor_tweet.get('source', 'N/A')}
- **Engagement**: {mejor_tweet.get('engagement_score', 0)}
- **ID**: [{mejor_tweet.get('id', 'N/A')}](https://twitter.com/i/status/{mejor_tweet.get('id', '')})
- **Archivo**: [[{Path(mejor_tweet.get('file', '')).stem}]]
"""
    
    if peor_tweet and peor_tweet != mejor_tweet:
        contenido += f"""### 📉 Menor Engagement

- **Fuente**: {peor_tweet.get('source', 'N/A')}
- **Engagement**: {peor_tweet.get('engagement_score', 0)}
- **ID**: [{peor_tweet.get('id', 'N/A')}](https://twitter.com/i/status/{peor_tweet.get('id', '')})
"""
    
    # Insights automáticos
    contenido += "\n## Insights\n\n"
    
    if por_fuente:
        mejor_fuente = max(por_fuente.items(), key=lambda x: x[1]["engagement"] / x[1]["count"] if x[1]["count"] > 0 else 0)
        contenido += f"- 🎯 **Mejor fuente**: {mejor_fuente[0]} (promedio {mejor_fuente[1]['engagement'] / mejor_fuente[1]['count'] if mejor_fuente[1]['count'] > 0 else 0:.1f})\n"
    
    if total_tweets > 0:
        contenido += f"- 📈 **Productividad**: {total_tweets / 7:.1f} tweets/día\n"
    
    contenido += f"""\n## Acciones Recomendadas

- [ ] Revisar tweets con bajo engagement
- [ ] Identificar patrones en tweets exitosos
- [ ] Planificar contenido para próxima semana
"""
    
    # Guardar reporte
    filepath = reports_dir / f"semana-{semana_str}.md"
    
    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📊 Reporte generado: {filepath.name}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error generando reporte: {e}")
        return None


def obtener_estadisticas_totales() -> dict:
    """Obtiene estadísticas totales de todos los tweets.

    Returns:
        Diccionario con estadísticas generales.
    """
    tweets = listar_tweets_en_vault()
    
    if not tweets:
        return {
            "total_tweets": 0,
            "engagement_total": 0,
            "engagement_promedio": 0,
            "por_fuente": {},
            "mejor_tweet": None,
        }
    
    total_engagement = sum(float(t.get("engagement_score", 0)) for t in tweets)
    
    por_fuente = {}
    for tweet in tweets:
        fuente = tweet.get("source", "unknown")
        if fuente not in por_fuente:
            por_fuente[fuente] = 0
        por_fuente[fuente] += 1
    
    mejor = max(tweets, key=lambda t: float(t.get("engagement_score", 0)))
    
    return {
        "total_tweets": len(tweets),
        "engagement_total": total_engagement,
        "engagement_promedio": total_engagement / len(tweets),
        "por_fuente": por_fuente,
        "mejor_tweet": mejor,
    }
