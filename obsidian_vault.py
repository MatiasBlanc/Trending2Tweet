"""Módulo para guardar tweets en bóveda de Obsidian.

Genera archivos Markdown con frontmatter de Obsidian
para crear una base de conocimiento de contenido.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ruta de la bóveda de Obsidian (configurable por variable de entorno)
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")

# Nombre de la carpeta dentro de la bóveda para los tweets
TWEETS_FOLDER = "Tweets"


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
    if not OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    
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
    if not OBSIDIAN_VAULT_PATH:
        return False
    
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    
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
    if not OBSIDIAN_VAULT_PATH:
        return []
    
    vault_path = Path(OBSIDIAN_VAULT_PATH)
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
