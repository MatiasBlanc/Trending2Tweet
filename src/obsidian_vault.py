"""Gestión de bóveda de Obsidian para tweets.

Guarda los tweets directamente en la carpeta configurada en OBSIDIAN_VAULT_PATH.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config

ATTACHMENTS_FOLDER = "attachments"


def _sanitize_filename(texto: str, max_length: int = 50) -> str:
    """Sanitiza un texto para usar como nombre de archivo."""
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    texto = re.sub(r'\s+', '-', texto.strip())
    texto = re.sub(r'-+', '-', texto)
    return texto[:max_length].rstrip('-')


def _get_vault_path() -> Optional[Path]:
    """Obtiene y valida la ruta de la bóveda de Obsidian."""
    if not config.OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    if not vault_path.exists():
        print(f"  ⚠️ Bóveda de Obsidian no encontrada: {vault_path}")
        return None
    
    return vault_path


def guardar_imagen_vault(
    image_bytes: bytes,
    nombre_archivo: str,
    source: str = "t2t",
) -> Optional[str]:
    """Guarda una imagen en la carpeta de attachments de la bóveda.

    Returns:
        Ruta relativa al vault de la imagen guardada, o None si falló.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None

    attachments_dir = vault_path / ATTACHMENTS_FOLDER
    attachments_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(nombre_archivo)
    fecha = datetime.now().strftime("%Y-%m-%d")
    filename = f"{fecha}_{safe_name}.png"
    filepath = attachments_dir / filename

    counter = 1
    while filepath.exists():
        filepath = attachments_dir / f"{fecha}_{safe_name}_{counter}.png"
        counter += 1

    try:
        filepath.write_bytes(image_bytes)
        return f"{ATTACHMENTS_FOLDER}/{filename}"
    except Exception as e:
        print(f"  ⚠️ Error guardando imagen: {e}")
        return None


def guardar_borrador(
    texto: str,
    source: str,
    titulo: Optional[str] = None,
    url: Optional[str] = None,
    repo_name: Optional[str] = None,
    repo_stars: Optional[int] = None,
    item_id: Optional[str] = None,
    prompt_file: Optional[str] = None,
    template_estilo: Optional[str] = None,
    notas: Optional[str] = None,
    imagen_path: Optional[str] = None,
) -> Optional[str]:
    """Guarda un tweet en la bóveda de Obsidian.

    Returns:
        Ruta del archivo creado, o None si no se pudo guardar.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    # Determinar carpeta según el tipo de fuente
    if source == "news":
        folder = vault_path / "T2T" / "news"
    else:
        folder = vault_path / "T2T" / "github"
    
    folder.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    fecha = now.strftime("%Y-%m-%d")
    
    if titulo:
        safe_title = _sanitize_filename(titulo)
    elif repo_name:
        safe_title = _sanitize_filename(repo_name.split("/")[-1])
    else:
        safe_title = _sanitize_filename(texto[:50])
    
    filename = f"{fecha}_{safe_title}.md"
    filepath = folder / filename
    
    counter = 1
    while filepath.exists():
        filepath = vault_path / f"{fecha}_{safe_title}_{counter}.md"
        counter += 1
    
    contenido = "---\n"
    contenido += f"type: tweet\n"
    contenido += f"status: draft\n"
    contenido += f"source: {source}\n"
    contenido += f"date: {now.isoformat()}\n"
    
    if url:
        contenido += f"url: {url}\n"
    if repo_name:
        contenido += f"repo: {repo_name}\n"
    if repo_stars:
        contenido += f"stars: {repo_stars}\n"
    if item_id:
        contenido += f"item_id: {item_id}\n"
    if prompt_file:
        contenido += f"prompt_file: {prompt_file}\n"
    if template_estilo:
        contenido += f"template: {template_estilo}\n"
    if imagen_path:
        contenido += f"imagen: {imagen_path}\n"
    
    contenido += "---\n\n"
    
    if titulo:
        contenido += f"# {titulo}\n\n"
    elif repo_name:
        contenido += f"# {repo_name}\n\n"
    
    if imagen_path:
        contenido += f"![Tarjeta]({imagen_path})\n\n"
    
    contenido += "## Tweet\n\n"
    contenido += f"{texto}\n\n"
    
    contenido += "## Metadata\n\n"
    contenido += f"- **Fuente**: {source}\n"
    contenido += f"- **Fecha**: {fecha}\n"
    contenido += f"- **Caracteres**: {len(texto)}\n"
    if url:
        contenido += f"- **URL**: {url}\n"
    if repo_stars:
        contenido += f"- **Stars**: {repo_stars}\n"
    
    if notas:
        contenido += f"\n## Notas\n\n{notas}\n"
    
    contenido += "\n## Revisión\n\n"
    contenido += "- [ ] Revisar ortografía\n"
    contenido += "- [ ] Verificar datos/fuentes\n"
    contenido += "- [ ] Agregar toque personal\n"
    contenido += "- [ ] Verificar longitud (280 chars)\n"
    contenido += "- [ ] Publicar en Twitter\n"
    
    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📝 Tweet guardado: {filepath.name}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error guardando tweet: {e}")
        return None


def listar_tweets() -> list[dict]:
    """Lista todos los tweets en la bóveda."""
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    tweets = []
    for md_file in vault_path.glob("**/*.md"):
        info = _parsear_frontmatter(md_file)
        if info:
            info["filepath"] = str(md_file)
            tweets.append(info)
    
    return sorted(tweets, key=lambda x: x.get("date", ""), reverse=True)


def _parsear_frontmatter(filepath: Path) -> Optional[dict]:
    """Parsea el frontmatter de un archivo Markdown."""
    try:
        content = filepath.read_text(encoding="utf-8")
        
        if not content.startswith("---"):
            return None
        
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return None
        
        frontmatter = content[3:end_idx].strip()
        info = {"filename": filepath.name}
        
        for line in frontmatter.split("\n"):
            if ":" in line and not line.strip().startswith("-"):
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip().strip('"')
        
        # Intentar extraer texto del tweet con formato estándar
        tweet_match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if tweet_match:
            info["tweet_text"] = tweet_match.group(1).strip()
        else:
            # Si no tiene sección "## Tweet", extraer texto después del frontmatter
            # (formato simplificado para tweets manuales)
            after_frontmatter = content[end_idx + 3:].strip()
            # Saltar título si existe (línea que empieza con #)
            lines = after_frontmatter.split("\n")
            tweet_lines = []
            started = False
            for line in lines:
                # Saltar líneas de título y líneas vacías iniciales
                if not started:
                    if line.startswith("# "):
                        info.setdefault("titulo", line[2:].strip())
                        continue
                    if line.strip() == "":
                        continue
                    started = True
                # Detenerse en siguiente sección
                if line.startswith("## "):
                    break
                tweet_lines.append(line)
            
            if tweet_lines:
                info["tweet_text"] = "\n".join(tweet_lines).strip()
        
        return info
    except Exception:
        return None


def obtener_tweet_para_publicar(filepath: str) -> Optional[str]:
    """Obtiene el texto del tweet de un archivo."""
    try:
        content = Path(filepath).read_text(encoding="utf-8")
        match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    except Exception:
        return None


def listar_borradores() -> list[dict]:
    """Lista solo los tweets con status draft de la carpeta de borradores."""
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    # Buscar solo en la carpeta de borradores
    borradores_path = vault_path / "T2T" / "borradores"
    
    if not borradores_path.exists():
        print(f"  ⚠️  Carpeta de borradores no encontrada: {borradores_path}")
        return []
    
    tweets = []
    for md_file in borradores_path.glob("**/*.md"):
        info = _parsear_frontmatter(md_file)
        if info:
            info["filepath"] = str(md_file)
            tweets.append(info)
    
    return sorted(tweets, key=lambda x: x.get("date", ""), reverse=True)


def obtener_tweet_por_id(tweet_id: str) -> Optional[dict]:
    """Obtiene un tweet por su ID (item_id o filename)."""
    tweets = listar_tweets()
    
    # Buscar por item_id
    for tweet in tweets:
        if tweet.get("item_id") == tweet_id:
            return tweet
    
    # Buscar por filename (sin extensión)
    for tweet in tweets:
        filename = Path(tweet["filepath"]).stem
        if filename == tweet_id or tweet.get("filename", "").replace(".md", "") == tweet_id:
            return tweet
    
    return None


def agregar_update_tweet(filepath: str, tweet_mejorado: str) -> bool:
    """Agrega una sección de update a un tweet existente.
    
    Args:
        filepath: Ruta al archivo del tweet.
        tweet_mejorado: Texto del tweet mejorado por la IA.
    
    Returns:
        True si se agregó correctamente, False en caso contrario.
    """
    try:
        content = Path(filepath).read_text(encoding="utf-8")
        
        # Detectar si es un hilo (contiene separadores ---)
        es_hilo = "\n---\n" in tweet_mejorado
        
        # Preparar el contenido del update
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if es_hilo:
            tweets = tweet_mejorado.split("\n---\n")
            update_content = "## Update\n\n"
            for tweet in tweets:
                update_content += f"{tweet.strip()}\n\n---\n\n"
            update_content += f"*Mejorado el {now}*\n\n"
        else:
            update_content = f"## Update\n\n{tweet_mejorado}\n\n---\n*Mejorado el {now}*\n\n"
        
        # Verificar si ya existe una sección Update
        if "## Update" in content:
            # Reemplazar la sección existente
            import re
            pattern = r"## Update.*?(?=\n## |$)"
            content = re.sub(pattern, update_content, content, flags=re.DOTALL)
        else:
            # Agregar nueva sección antes de "## Revisión" o al final
            if "## Revisión" in content:
                content = content.replace(
                    "## Revisión",
                    f"{update_content}## Revisión"
                )
            else:
                content += f"\n\n{update_content}"
        
        Path(filepath).write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  ⚠️ Error agregando update: {e}")
        return False


def obtener_estadisticas() -> dict:
    """Obtiene estadísticas generales de la bóveda."""
    tweets = listar_tweets()
    
    return {
        "total_tweets": len(tweets),
        "borradores": len([t for t in tweets if t.get("status") == "draft"]),
        "publicados": len([t for t in tweets if t.get("status") == "published"]),
    }
