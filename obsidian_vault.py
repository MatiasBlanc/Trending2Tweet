"""Módulo para gestionar tweets en bóveda de Obsidian.

Flujo de trabajo:
- borradores: tweets generados por el bot (pendientes de revisión)
- listos: tweets editados y listos para publicar
- publicados: tweets ya en Twitter (con link)

Subcarpetas:
- T2T/: tweets automáticos (noticias, github trending)
- manual/: tweets escritos por el usuario
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

# ── Estructura de carpetas ────────────────────────────────────
T2T_FOLDER = "T2T"
MANUAL_FOLDER = "manual"
BORRADORES = "borradores"
LISTOS = "listos"
PUBLICADOS = "publicados"
TEMPLATES_FOLDER = "Templates"
CALENDAR_FOLDER = "Calendar"
REPORTS_FOLDER = "Reports"
ANALYTICS_FOLDER = "analytics"


def _sanitize_filename(texto: str, max_length: int = 50) -> str:
    """Sanitiza un texto para usar como nombre de archivo.

    Args:
        texto: Texto a sanitizar.
        max_length: Longitud máxima del nombre.

    Returns:
        Nombre de archivo seguro.
    """
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    texto = re.sub(r'\s+', '-', texto.strip())
    texto = re.sub(r'-+', '-', texto)
    return texto[:max_length].rstrip('-')


def _get_vault_path() -> Optional[Path]:
    """Obtiene y valida la ruta de la bóveda de Obsidian.

    Returns:
        Path de la bóveda o None si no está configurada.
    """
    if not config.OBSIDIAN_VAULT_PATH:
        return None
    
    vault_path = Path(config.OBSIDIAN_VAULT_PATH)
    if not vault_path.exists():
        print(f"  ⚠️ Bóveda de Obsidian no encontrada: {vault_path}")
        return None
    
    return vault_path


# ── Guardar Borradores ────────────────────────────────────────


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
) -> Optional[str]:
    """Guarda un tweet como borrador en la bóveda de Obsidian.

    Los borradores son tweets generados por el bot que necesitan
    revisión antes de ser publicados.

    Args:
        texto: Contenido del tweet generado.
        source: Fuente (news, github, github_manual, manual).
        titulo: Título descriptivo del tweet.
        url: URL de la fuente original.
        repo_name: Nombre del repo (si es de GitHub).
        repo_stars: Stars del repo (si es de GitHub).
        item_id: ID del item procesado.
        prompt_file: Ruta del prompt usado.
        template_estilo: Estilo de gancho usado.
        notas: Notas adicionales.

    Returns:
        Ruta del archivo creado, o None si no se pudo guardar.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    # Determinar carpeta base según la fuente
    if source.startswith("manual"):
        base_folder = MANUAL_FOLDER
    else:
        base_folder = T2T_FOLDER
    
    # Crear estructura de carpetas
    borradores_dir = vault_path / base_folder / BORRADORES
    borradores_dir.mkdir(parents=True, exist_ok=True)
    
    # Fecha actual
    now = datetime.now()
    fecha = now.strftime("%Y-%m-%d")
    
    # Generar nombre de archivo
    if titulo:
        safe_title = _sanitize_filename(titulo)
    elif repo_name:
        safe_title = _sanitize_filename(repo_name.split("/")[-1])
    else:
        safe_title = _sanitize_filename(texto[:50])
    
    filename = f"{fecha}_{safe_title}.md"
    filepath = borradores_dir / filename
    
    # Si ya existe, agregar sufijo
    counter = 1
    while filepath.exists():
        filepath = borradores_dir / f"{fecha}_{safe_title}_{counter}.md"
        counter += 1
    
    # Construir frontmatter
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
    
    contenido += "---\n\n"
    
    # Título
    if titulo:
        contenido += f"# {titulo}\n\n"
    elif repo_name:
        contenido += f"# {repo_name}\n\n"
    
    # Tweet generado
    contenido += "## Tweet\n\n"
    contenido += f"{texto}\n\n"
    
    # Metadata
    contenido += "## Metadata\n\n"
    contenido += f"- **Fuente**: {source}\n"
    contenido += f"- **Fecha**: {fecha}\n"
    contenido += f"- **Caracteres**: {len(texto)}\n"
    if url:
        contenido += f"- **URL**: {url}\n"
    if repo_stars:
        contenido += f"- **Stars**: {repo_stars}\n"
    
    # Notas
    if notas:
        contenido += f"\n## Notas\n\n{notas}\n"
    
    # Checklist de revisión
    contenido += "\n## Revisión\n\n"
    contenido += "- [ ] Revisar ortografía\n"
    contenido += "- [ ] Verificar datos/fuentes\n"
    contenido += "- [ ] Agregar toque personal\n"
    contenido += "- [ ] Verificar longitud (280 chars)\n"
    contenido += "- [ ] Mover a 'listos' cuando esté listo\n"
    
    # Escribir archivo
    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📝 Borrador guardado: {filepath.name}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error guardando borrador: {e}")
        return None


# ── Mover entre estados ───────────────────────────────────────


def mover_a_listos(filepath: str) -> Optional[str]:
    """Mueve un borrador a la carpeta de listos para publicar.

    Args:
        filepath: Ruta del archivo borrador.

    Returns:
        Ruta del nuevo archivo, o None si falló.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    src = Path(filepath)
    if not src.exists():
        print(f"  ⚠️ Archivo no encontrado: {filepath}")
        return None
    
    # Determinar carpeta destino
    # Detectar si es T2T o manual basado en la ruta
    if T2T_FOLDER in str(src):
        dest_dir = vault_path / T2T_FOLDER / LISTOS
    else:
        dest_dir = vault_path / MANUAL_FOLDER / LISTOS
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    
    # Si ya existe, agregar sufijo
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    
    try:
        # Leer contenido y actualizar status
        content = src.read_text(encoding="utf-8")
        content = content.replace("status: draft", "status: ready")
        dest.write_text(content, encoding="utf-8")
        
        # Eliminar original
        src.unlink()
        
        print(f"  ✅ Movido a listos: {dest.name}")
        return str(dest)
    except Exception as e:
        print(f"  ⚠️ Error moviendo archivo: {e}")
        return None


def marcar_como_publicado(
    filepath: str,
    tweet_url: str,
    tweet_id: Optional[str] = None,
) -> Optional[str]:
    """Marca un tweet como publicado y lo mueve a publicados.

    Args:
        filepath: Ruta del archivo listo para publicar.
        tweet_url: URL del tweet publicado.
        tweet_id: ID del tweet en Twitter.

    Returns:
        Ruta del archivo actualizado, o None si falló.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    src = Path(filepath)
    if not src.exists():
        print(f"  ⚠️ Archivo no encontrado: {filepath}")
        return None
    
    # Determinar carpeta destino
    if T2T_FOLDER in str(src):
        dest_dir = vault_path / T2T_FOLDER / PUBLICADOS
    else:
        dest_dir = vault_path / MANUAL_FOLDER / PUBLICADOS
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    
    try:
        # Leer contenido y actualizar
        content = src.read_text(encoding="utf-8")
        
        # Actualizar frontmatter
        content = content.replace("status: ready", "status: published")
        content = content.replace("status: draft", "status: published")
        
        # Agregar campos de publicación al frontmatter
        now = datetime.now().isoformat()
        publicacion = f"published_at: {now}\ntweet_url: {tweet_url}\n"
        if tweet_id:
            publicacion += f"tweet_id: {tweet_id}\n"
        
        # Insertar después de la primera línea de ---
        content = content.replace("---\n", f"---\n{publicacion}", 1)
        
        # Agregar sección de publicación
        content += f"\n## Publicación\n\n"
        content += f"- **Publicado**: {now}\n"
        content += f"- **URL**: [{tweet_url}]({tweet_url})\n"
        if tweet_id:
            content += f"- **Tweet ID**: {tweet_id}\n"
        
        dest.write_text(content, encoding="utf-8")
        src.unlink()
        
        print(f"  🐦 Marcado como publicado: {dest.name}")
        return str(dest)
    except Exception as e:
        print(f"  ⚠️ Error marcando como publicado: {e}")
        return None


# ── Listar tweets ─────────────────────────────────────────────


def listar_borradores(source: Optional[str] = None) -> list[dict]:
    """Lista todos los borradores pendientes.

    Args:
        source: Filtrar por fuente (t2t, manual, o None para todos).

    Returns:
        Lista de borradores con su metadata.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    borradores = []
    carpetas = []
    
    if source == "t2t":
        carpetas = [vault_path / T2T_FOLDER / BORRADORES]
    elif source == "manual":
        carpetas = [vault_path / MANUAL_FOLDER / BORRADORES]
    else:
        carpetas = [
            vault_path / T2T_FOLDER / BORRADORES,
            vault_path / MANUAL_FOLDER / BORRADORES,
        ]
    
    for carpeta in carpetas:
        if not carpeta.exists():
            continue
        
        for md_file in carpeta.glob("*.md"):
            info = _parsear_frontmatter(md_file)
            if info:
                info["filepath"] = str(md_file)
                info["folder"] = "t2t" if T2T_FOLDER in str(md_file) else "manual"
                borradores.append(info)
    
    return sorted(borradores, key=lambda x: x.get("date", ""), reverse=True)


def listar_listos() -> list[dict]:
    """Lista todos los tweets listos para publicar.

    Returns:
        Lista de tweets listos con su metadata.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    listos = []
    
    for carpeta_base in [T2T_FOLDER, MANUAL_FOLDER]:
        carpeta = vault_path / carpeta_base / LISTOS
        if not carpeta.exists():
            continue
        
        for md_file in carpeta.glob("*.md"):
            info = _parsear_frontmatter(md_file)
            if info:
                info["filepath"] = str(md_file)
                info["folder"] = carpeta_base
                listos.append(info)
    
    return sorted(listos, key=lambda x: x.get("date", ""), reverse=True)


def listar_publicados(source: Optional[str] = None) -> list[dict]:
    """Lista todos los tweets publicados.

    Args:
        source: Filtrar por fuente (t2t, manual, o None para todos).

    Returns:
        Lista de tweets publicados con su metadata.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    publicados = []
    carpetas = []
    
    if source == "t2t":
        carpetas = [vault_path / T2T_FOLDER / PUBLICADOS]
    elif source == "manual":
        carpetas = [vault_path / MANUAL_FOLDER / PUBLICADOS]
    else:
        carpetas = [
            vault_path / T2T_FOLDER / PUBLICADOS,
            vault_path / MANUAL_FOLDER / PUBLICADOS,
        ]
    
    for carpeta in carpetas:
        if not carpeta.exists():
            continue
        
        for md_file in carpeta.glob("*.md"):
            info = _parsear_frontmatter(md_file)
            if info:
                info["filepath"] = str(md_file)
                publicados.append(info)
    
    return sorted(publicados, key=lambda x: x.get("published_at", ""), reverse=True)


def _parsear_frontmatter(filepath: Path) -> Optional[dict]:
    """Parsea el frontmatter de un archivo Markdown.

    Args:
        filepath: Ruta del archivo.

    Returns:
        Diccionario con la metadata o None si no se pudo parsear.
    """
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
        
        # Extraer el tweet del contenido
        tweet_match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if tweet_match:
            info["tweet_text"] = tweet_match.group(1).strip()
        
        return info
    except Exception:
        return None


# ── Obtener tweet para publicar ───────────────────────────────


def obtener_tweet_para_publicar(filepath: str) -> Optional[str]:
    """Obtiene el texto del tweet de un archivo listo para publicar.

    Args:
        filepath: Ruta del archivo.

    Returns:
        Texto del tweet o None si no se encontró.
    """
    try:
        content = Path(filepath).read_text(encoding="utf-8")
        
        # Buscar sección "## Tweet"
        match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None
    except Exception:
        return None


# ── Analytics ─────────────────────────────────────────────────


def guardar_analytics(csv_path: str, mes: Optional[str] = None) -> Optional[str]:
    """Guarda un CSV de Twitter Analytics en la bóveda.

    Args:
        csv_path: Ruta al archivo CSV.
        mes: Mes en formato YYYY-MM (opcional, se detecta del CSV).

    Returns:
        Ruta del archivo guardado, o None si falló.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    analytics_dir = vault_path / ANALYTICS_FOLDER
    analytics_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path(csv_path)
    if not src.exists():
        print(f"  ⚠️ CSV no encontrado: {csv_path}")
        return None
    
    # Detectar mes del nombre del archivo o usar el proporcionado
    if not mes:
        # Intentar detectar del nombre: analytics_2026-07.csv
        match = re.search(r'(\d{4}-\d{2})', src.name)
        if match:
            mes = match.group(1)
        else:
            mes = datetime.now().strftime("%Y-%m")
    
    dest = analytics_dir / f"{mes}.csv"
    
    try:
        import shutil
        shutil.copy2(src, dest)
        print(f"  📊 Analytics guardado: {dest.name}")
        return str(dest)
    except Exception as e:
        print(f"  ⚠️ Error guardando analytics: {e}")
        return None


def obtener_analytics() -> list[dict]:
    """Obtiene resumen de los analytics disponibles.

    Returns:
        Lista de diccionarios con info de cada CSV.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    analytics_dir = vault_path / ANALYTICS_FOLDER
    if not analytics_dir.exists():
        return []
    
    analytics = []
    
    for csv_file in sorted(analytics_dir.glob("*.csv"), reverse=True):
        try:
            # Leer primera línea para obtener headers
            with open(csv_file, "r", encoding="utf-8") as f:
                headers = f.readline().strip().split(",")
            
            # Contar líneas (excluyendo header)
            with open(csv_file, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f) - 1
            
            analytics.append({
                "file": str(csv_file),
                "filename": csv_file.name,
                "mes": csv_file.stem,
                "columns": len(headers),
                "tweets": line_count,
            })
        except Exception:
            continue
    
    return analytics


# ── Estadísticas ──────────────────────────────────────────────


def obtener_estadisticas() -> dict:
    """Obtiene estadísticas generales de la bóveda.

    Returns:
        Diccionario con estadísticas.
    """
    borradores = listar_borradores()
    listos = listar_listos()
    publicados = listar_publicados()
    analytics = obtener_analytics()
    
    return {
        "borradores": len(borradores),
        "listos": len(listos),
        "publicados": len(publicados),
        "analytics_months": len(analytics),
        "borradores_t2t": len([b for b in borradores if b.get("folder") == "t2t"]),
        "borradores_manual": len([b for b in borradores if b.get("folder") == "manual"]),
    }


# ── Compatibilidad con código anterior ────────────────────────
# Estas funciones mantienen compatibilidad con el código existente

TWEETS_FOLDER = T2T_FOLDER  # Alias para compatibilidad


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
    """Función de compatibilidad. Usa guardar_borrador() para nuevos tweets."""
    return guardar_borrador(
        texto=texto,
        source=source,
        titulo=title,
        url=url,
        item_id=item_id,
        prompt_file=prompt_file,
        template_estilo=template_estilo,
    )


def listar_tweets_en_vault(source: Optional[str] = None) -> list[dict]:
    """Función de compatibilidad. Lista todos los tweets."""
    todos = listar_borradores(source) + listar_listos() + listar_publicados(source)
    return todos


def actualizar_metricas_en_vault(
    tweet_id: str,
    likes: int,
    retweets: int,
    replies: int,
    impressions: int,
    bookmarks: int = 0,
) -> bool:
    """Actualiza métricas de un tweet publicado.

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
    vault_path = _get_vault_path()
    if not vault_path:
        return False
    
    # Buscar en publicados
    for carpeta_base in [T2T_FOLDER, MANUAL_FOLDER]:
        carpeta = vault_path / carpeta_base / PUBLICADOS
        if not carpeta.exists():
            continue
        
        for md_file in carpeta.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                
                if f"tweet_id: {tweet_id}" not in content:
                    continue
                
                # Actualizar métricas
                metricas = (
                    "## Métricas\n\n"
                    f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
                    f"- ❤️ Likes: {likes}\n"
                    f"- 🔁 Retweets: {retweets}\n"
                    f"- 💬 Replies: {replies}\n"
                    f"- 👁 Impressions: {impressions}\n"
                    f"- 🔖 Bookmarks: {bookmarks}\n"
                )
                
                patron = r"## Métricas\n\n.*?(?=\n## |\Z)"
                contenido_nuevo = re.sub(patron, metricas, content, flags=re.DOTALL)
                
                md_file.write_text(contenido_nuevo, encoding="utf-8")
                return True
            except Exception:
                continue
    
    return False


# ── Templates (se mantienen igual) ────────────────────────────


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
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    templates_dir = vault_path / TEMPLATES_FOLDER
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = _sanitize_filename(nombre)
    filepath = templates_dir / f"{safe_name}.md"
    
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
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    templates_dir = vault_path / TEMPLATES_FOLDER
    if not templates_dir.exists():
        return []
    
    templates = []
    
    for md_file in templates_dir.glob("*.md"):
        info = _parsear_frontmatter(md_file)
        if info:
            templates.append(info)
    
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
            filepath = Path(template.get("filename", ""))
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
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
        tipo: Tipo de publicación (news, github, manual, thread).
        tema: Tema o título del tweet.
        notas: Notas adicionales.

    Returns:
        Ruta del archivo actualizado, o None si falló.
    """
    vault_path = _get_vault_path()
    if not vault_path:
        return None
    
    calendar_dir = vault_path / CALENDAR_FOLDER
    calendar_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = calendar_dir / f"{fecha}.md"
    
    if filepath.exists():
        contenido = filepath.read_text(encoding="utf-8")
    else:
        contenido = f"---\ndate: {fecha}\ntype: calendar\n---\n\n# Calendario Editorial - {fecha}\n\n"
    
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
    vault_path = _get_vault_path()
    if not vault_path:
        return []
    
    calendar_dir = vault_path / CALENDAR_FOLDER
    if not calendar_dir.exists():
        return []
    
    from datetime import timedelta
    
    if semana:
        inicio = datetime.strptime(semana, "%Y-%m-%d")
    else:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=hoy.weekday())
    
    entradas = []
    
    for i in range(7):
        fecha = (inicio + timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = calendar_dir / f"{fecha}.md"
        
        if not filepath.exists():
            continue
        
        try:
            content = filepath.read_text(encoding="utf-8")
            
            for line in content.split("\n"):
                if line.strip().startswith("- ["):
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
