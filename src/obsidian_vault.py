"""Gestión de bóveda de Obsidian para tweets organizados por categoría.

Estructura de carpetas:
~/Obsidian/Twitter/bot/
├── teclado/     (posts sobre teclados y periféricos)
├── github/      (repos trending y manuales)
├── news/        (noticias tech de Hacker News)
├── codigo/      (noticias y tips sobre programación)
└── archivados/  (tweets marcados como published)
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config

CATEGORIAS_VALIDAS = ("teclado", "github", "news", "codigo")

_ALIAS_CATEGORIAS = {
    "teclados": "teclado",
    "teclado": "teclado",
    "keyboard": "teclado",
    "keyboards": "teclado",
    "github": "github",
    "github_trending": "github",
    "github_manual": "github",
    "gh": "github",
    "news": "news",
    "tech_news": "news",
    "hacker_news": "news",
    "hn": "news",
    "codigo": "codigo",
    "code": "codigo",
    "programacion": "codigo",
}


def normalizar_categoria(cat: Optional[str]) -> str:
    """Normaliza el nombre de una categoría."""
    if not cat:
        return "news"
    cat_lower = cat.strip().lower()
    return _ALIAS_CATEGORIAS.get(cat_lower, cat_lower)


def _categoria_segura(cat: Optional[str]) -> str:
    """Devuelve una categoría válida para construir rutas dentro de la bóveda."""
    categoria = normalizar_categoria(cat)
    return categoria if categoria in CATEGORIAS_VALIDAS else "news"


def _esta_dentro_de(ruta: Path, raiz: Path) -> bool:
    """Indica si una ruta resuelta pertenece a una raíz autorizada."""
    try:
        ruta.relative_to(raiz)
        return True
    except ValueError:
        return False


def _ruta_en_boveda(filepath: Path, permitir_archivados: bool = True) -> Optional[Path]:
    """Valida que una ruta Markdown resuelta permanezca dentro de la bóveda.

    La resolución previa evita que un enlace simbólico o segmentos ``..``
    permitan leer, modificar o borrar archivos fuera de la bóveda configurada.
    """
    vault_path = _get_vault_path(crear=False)
    twitter_path = _get_twitter_vault_path(crear=False)
    if (not vault_path and not twitter_path) or filepath.suffix.lower() != ".md":
        return None

    try:
        ruta_resuelta = filepath.expanduser().resolve(strict=True)
        raices: list[Path] = []
        if vault_path:
            raices.append(vault_path.resolve(strict=True))
        if twitter_path:
            raiz_twitter = twitter_path.resolve(strict=True)
            if raiz_twitter not in raices:
                raices.append(raiz_twitter)
        if not any(_esta_dentro_de(ruta_resuelta, raiz) for raiz in raices):
            return None
    except (FileNotFoundError, OSError, ValueError):
        return None

    if not permitir_archivados:
        for raiz in raices:
            if _esta_dentro_de(ruta_resuelta, raiz / "archivados"):
                return None

    return ruta_resuelta


def _sanitize_filename(texto: str, max_length: int = 50) -> str:
    """Sanitiza un texto para usar como nombre de archivo."""
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9\s-]", "", texto)
    texto = re.sub(r"\s+", "-", texto.strip())
    texto = re.sub(r"-+", "-", texto)
    return texto[:max_length].rstrip("-")


def _texto_unilinea(valor: object) -> str:
    """Convierte metadatos externos en texto de una sola línea."""
    return str(valor).replace("\r", " ").replace("\n", " ").strip()


def _valor_frontmatter(valor: object) -> str:
    """Cita un valor dinámico para impedir que rompa el frontmatter YAML."""
    texto = _texto_unilinea(valor).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{texto}"'


def _get_vault_path(crear: bool = True) -> Optional[Path]:
    """Obtiene y valida la ruta de la bóveda de Obsidian."""
    if not config.OBSIDIAN_VAULT_PATH:
        return None

    vault_path = Path(os.path.expanduser(config.OBSIDIAN_VAULT_PATH))
    if crear and not vault_path.exists():
        try:
            vault_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"  ⚠️ Error creando ruta de la bóveda: {e}")
            return None

    if not vault_path.is_dir():
        print(f"  ⚠️ La ruta de la bóveda no es una carpeta: {vault_path}")
        return None

    return vault_path


def _get_twitter_vault_path(crear: bool = False) -> Optional[Path]:
    """Obtiene y valida la ruta raíz de la bóveda de Twitter completa.

    Abarca toda la carpeta de Twitter en Obsidian (ej. .../02_Areas/Twitter),
    incluyendo subcarpetas como 'bot/' o 'sponsors/' y las notas sueltas.
    """
    path_str = getattr(config, "TWITTER_VAULT_PATH", None)
    if path_str:
        twitter_path = Path(os.path.expanduser(path_str))
        if twitter_path.is_dir():
            return twitter_path
        if crear:
            try:
                twitter_path.mkdir(parents=True, exist_ok=True)
                return twitter_path
            except Exception as e:
                print(f"  ⚠️ Error creando ruta de la bóveda de Twitter: {e}")

    vault_path = _get_vault_path(crear=False)
    if not vault_path:
        return None

    if vault_path.name.lower() == "bot" and vault_path.parent.exists():
        return vault_path.parent

    for p in [vault_path] + list(vault_path.parents):
        if p.name.lower() == "twitter" and p.exists():
            return p

    return vault_path


def _get_category_path(categoria: str, crear: bool = True) -> Optional[Path]:
    """Obtiene la carpeta de una categoría dentro de la bóveda.

    Args:
        categoria: Nombre de la categoría (teclado, github, news, codigo).
        crear: Crea la carpeta si no existe.

    Returns:
        Ruta de la carpeta o None.
    """
    vault_path = _get_vault_path(crear=crear)
    if not vault_path:
        return None

    cat_norm = _categoria_segura(categoria)
    cat_path = vault_path / cat_norm
    if crear:
        cat_path.mkdir(parents=True, exist_ok=True)
    elif not cat_path.exists():
        return None

    return cat_path


def _get_archivados_path(
    categoria: Optional[str] = None, crear: bool = True
) -> Optional[Path]:
    """Obtiene la carpeta de archivados dentro de la bóveda."""
    vault_path = _get_vault_path(crear=crear)
    if not vault_path:
        return None

    archivados_path = vault_path / "archivados"
    if categoria:
        cat_norm = _categoria_segura(categoria)
        archivados_path = archivados_path / cat_norm

    if crear:
        archivados_path.mkdir(parents=True, exist_ok=True)
    elif not archivados_path.exists():
        return None

    return archivados_path


def archivar_publicados() -> list[dict]:
    """Escanea la bóveda y mueve a 'archivados/' los tweets marcados como published.

    Returns:
        Lista de tweets que fueron movidos a la carpeta archivados.
    """
    vault_path = _get_vault_path(crear=False)
    if not vault_path:
        return []

    archivados_base = vault_path / "archivados"
    movidos = []

    # Recorrer archivos .md en todas las subcarpetas excepto archivados
    for md_file in vault_path.glob("**/*.md"):
        # Ignorar lo que ya esté en archivados
        if archivados_base in md_file.parents or md_file.parent == archivados_base:
            continue

        info = _parsear_frontmatter(md_file)
        if not info:
            continue

        status = str(info.get("status", "")).strip().lower()
        published_flag = str(info.get("published", "")).strip().lower()

        # Si está marcado como published/publicado/archivado
        if status in ("published", "publicado", "archivado", "archived") or published_flag in ("true", "1", "yes", "si"):
            categoria = _categoria_segura(
                info.get("category") or md_file.parent.name
            )
            dest_folder = _get_archivados_path(categoria=categoria, crear=True)
            if not dest_folder:
                dest_folder = _get_archivados_path(crear=True)

            if not dest_folder:
                continue

            dest_file = dest_folder / md_file.name
            counter = 1
            while dest_file.exists() and dest_file != md_file:
                dest_file = dest_folder / f"{md_file.stem}_{counter}.md"
                counter += 1

            try:
                shutil.move(str(md_file), str(dest_file))
                info["old_filepath"] = str(md_file)
                info["filepath"] = str(dest_file)
                movidos.append(info)
                print(f"  📦 Archivado tweet publicado: {md_file.name} → archivados/{categoria}/")
            except Exception as e:
                print(f"  ⚠️ Error archivando {md_file.name}: {e}")

    return movidos


def guardar_borrador(
    texto: str,
    categoria: str,
    source: str,
    titulo: Optional[str] = None,
    url: Optional[str] = None,
    repo_name: Optional[str] = None,
    repo_stars: Optional[int] = None,
    item_id: Optional[str] = None,
    prompt_file: Optional[str] = None,
    template_estilo: Optional[str] = None,
    notas: Optional[str] = None,
    dificultad: Optional[str] = None,
) -> Optional[str]:
    """Guarda un tweet en la carpeta correspondiente a su categoría.

    Args:
        texto: Texto del tweet generado.
        categoria: Categoría ('teclado', 'github', 'news', 'codigo').
        source: Identificador de la fuente (ej. 'github_trending', 'news', 'reddit').
        titulo: Título opcional.
        url: URL opcional.
        repo_name: Nombre de repositorio si aplica.
        repo_stars: Cantidad de stars si aplica.
        item_id: ID del item.
        prompt_file: Archivo de prompt utilizado.
        template_estilo: Nombre de la plantilla o estilo.
        notas: Notas adicionales.
        dificultad: Nivel de dificultad si aplica (ej. 'facil', 'medio', 'dificil').

    Returns:
        Ruta del archivo creado, o None si no se pudo guardar.
    """
    cat_norm = _categoria_segura(categoria)
    folder = _get_category_path(cat_norm, crear=True)
    if not folder:
        return None

    # Archivar cualquier tweet previamente publicado
    archivar_publicados()

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
        filepath = folder / f"{fecha}_{safe_title}_{counter}.md"
        counter += 1

    contenido = "---\n"
    contenido += "type: tweet\n"
    contenido += "status: draft\n"
    contenido += f"category: {_valor_frontmatter(cat_norm)}\n"
    contenido += f"source: {_valor_frontmatter(source)}\n"
    contenido += f"date: {_valor_frontmatter(now.isoformat())}\n"

    if url:
        contenido += f"url: {_valor_frontmatter(url)}\n"
    if repo_name:
        contenido += f"repo: {_valor_frontmatter(repo_name)}\n"
    if repo_stars is not None:
        contenido += f"stars: {repo_stars}\n"
    if item_id:
        contenido += f"item_id: {_valor_frontmatter(item_id)}\n"
    if prompt_file:
        contenido += f"prompt_file: {_valor_frontmatter(prompt_file)}\n"
    if template_estilo:
        contenido += f"template: {_valor_frontmatter(template_estilo)}\n"
    if dificultad:
        contenido += f"dificultad: {_valor_frontmatter(dificultad)}\n"
    contenido += "---\n\n"

    if titulo:
        contenido += f"# {_texto_unilinea(titulo)}\n\n"
    elif repo_name:
        contenido += f"# {_texto_unilinea(repo_name)}\n\n"

    contenido += "## Tweet\n\n"
    contenido += f"{texto}\n\n"

    contenido += "## Metadata\n\n"
    contenido += f"- **Categoría**: {cat_norm}\n"
    if dificultad:
        contenido += f"- **Dificultad**: {dificultad.capitalize()}\n"
    contenido += f"- **Fuente**: {source}\n"
    contenido += f"- **Fecha**: {fecha}\n"
    contenido += f"- **Caracteres**: {len(texto)}\n"
    if url:
        contenido += f"- **URL**: {url}\n"
    if repo_stars is not None:
        contenido += f"- **Stars**: {repo_stars}\n"

    if notas:
        contenido += f"\n## Notas\n\n{notas}\n"

    contenido += "\n## Revisión\n\n"
    contenido += "- [ ] Revisar ortografía\n"
    contenido += "- [ ] Verificar datos/fuentes\n"
    contenido += "- [ ] Agregar toque personal\n"
    contenido += "- [ ] Verificar longitud\n"
    contenido += "- [ ] Publicar en Twitter\n"

    try:
        filepath.write_text(contenido, encoding="utf-8")
        print(f"  📝 Tweet guardado en [{cat_norm}]: {filepath.name}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️ Error guardando tweet: {e}")
        return None


def marcar_como_publicado(
    filepath: str, tweet_id: Optional[str] = None
) -> Optional[str]:
    """Marca un tweet como publicado en el frontmatter y lo mueve a 'archivados/'.

    Args:
        filepath: Ruta del archivo actual.
        tweet_id: ID devuelto por Twitter tras publicar.

    Returns:
        Nueva ruta del archivo en archivados, o None si falló.
    """
    path = _ruta_en_boveda(Path(filepath), permitir_archivados=False)
    if not path:
        print(f"  ⚠️ Archivo Markdown fuera de la bóveda o no encontrado: {filepath}")
        return None

    try:
        content = path.read_text(encoding="utf-8")
        info = _parsear_frontmatter(path) or {}
        categoria = _categoria_segura(
            info.get("category") or path.parent.name
        )

        # Actualizar status en frontmatter
        now_str = datetime.now().isoformat()
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                fm = content[3:end_idx]
                if re.search(r"^status\s*:.*$", fm, re.MULTILINE):
                    fm = re.sub(r"^status\s*:.*$", "status: published", fm, flags=re.MULTILINE)
                else:
                    fm += "\nstatus: published"

                if tweet_id:
                    fm += f"\ntweet_id: {_valor_frontmatter(tweet_id)}"
                fm += f"\npublished_at: {now_str}\n"

                content = f"---{fm}---" + content[end_idx + 3:]

        # Mover a archivados
        dest_folder = _get_archivados_path(categoria=categoria, crear=True)
        if not dest_folder:
            print("  ⚠️ No se pudo preparar la carpeta de archivados.")
            return None

        dest_file = dest_folder / path.name
        counter = 1
        while dest_file.exists() and dest_file != path:
            dest_file = dest_folder / f"{path.stem}_{counter}.md"
            counter += 1

        # Escribir primero evita perder la nota si el destino no es escribible.
        dest_file.write_text(content, encoding="utf-8")
        path.unlink()
        print(f"  📦 Tweet publicado y archivado en: {dest_file.relative_to(dest_file.parent.parent.parent)}")
        return str(dest_file)
    except Exception as e:
        print(f"  ⚠️ Error marcando como publicado: {e}")
        return None


def listar_tweets(
    categoria: Optional[str] = None, incluir_archivados: bool = False
) -> list[dict]:
    """Lista los tweets en la bóveda, opcionalmente filtrados por categoría."""
    vault_path = _get_vault_path(crear=False)
    if not vault_path:
        return []

    # Mantener archivados al día
    archivar_publicados()

    archivados_base = vault_path / "archivados"
    tweets = []

    for md_file in vault_path.glob("**/*.md"):
        es_archivado = archivados_base in md_file.parents or md_file.parent == archivados_base
        if es_archivado and not incluir_archivados:
            continue

        info = _parsear_frontmatter(md_file)
        if info:
            cat = normalizar_categoria(info.get("category") or md_file.parent.name)
            if categoria and cat != normalizar_categoria(categoria):
                continue
            info["filepath"] = str(md_file)
            info["category"] = cat
            info["is_archived"] = es_archivado
            tweets.append(info)

    return sorted(tweets, key=lambda x: x.get("date", ""), reverse=True)


def listar_tweets_boveda(
    solo_con_texto: bool = True,
    incluir_archivados: bool = True,
    categoria: Optional[str] = None,
) -> list[dict]:
    """Lista los tweets en toda la bóveda de Twitter (raíz, subcarpetas, bot, archivados).

    Args:
        solo_con_texto: Si es True, filtra notas que no tengan texto de tweet para mejorar.
        incluir_archivados: Si es True, incluye tweets que están archivados o publicados.
        categoria: Filtro opcional por categoría.

    Returns:
        Lista de diccionarios con información de cada tweet, ordenada por fecha o mtime descendente.
    """
    twitter_vault = _get_twitter_vault_path(crear=False)
    if not twitter_vault or not twitter_vault.exists():
        twitter_vault = _get_vault_path(crear=False)
        if not twitter_vault:
            return []

    archivados_base = twitter_vault / "archivados"
    bot_archivados = twitter_vault / "bot" / "archivados"
    tweets = []

    for md_file in twitter_vault.glob("**/*.md"):
        # Ignorar archivos ocultos o dashboards
        if md_file.name.startswith((".", "_")):
            continue
        # Ignorar carpetas ocultas
        if any(p.startswith(".") for p in md_file.parts):
            continue

        es_archivado = (
            (archivados_base.exists() and (archivados_base in md_file.parents or md_file.parent == archivados_base))
            or (bot_archivados.exists() and (bot_archivados in md_file.parents or md_file.parent == bot_archivados))
        )

        if es_archivado and not incluir_archivados:
            continue

        info = _parsear_frontmatter(md_file)
        if not info:
            continue

        try:
            rel_path = md_file.relative_to(twitter_vault)
            parent_rel = str(rel_path.parent)
            ubicacion = "twitter/" if parent_rel == "." else f"{parent_rel}/"
        except ValueError:
            ubicacion = f"{md_file.parent.name}/"
            rel_path = md_file.name

        info["relative_path"] = str(rel_path)
        info["ubicacion"] = ubicacion
        info["is_archived"] = es_archivado

        raw_status = str(info.get("status", "")).strip().lower()
        raw_pub = str(info.get("published", "")).strip().lower()
        if raw_status in ("published", "publicado", "archivado", "archived") or raw_pub in ("true", "1", "yes", "si") or es_archivado:
            info["status"] = "published"
        else:
            info["status"] = "draft"

        cat_info = info.get("category")
        if not cat_info:
            if md_file.parent != twitter_vault and md_file.parent.name not in ("Twitter", "bot"):
                cat_info = md_file.parent.name
            else:
                cat_info = "general"
        info["category"] = normalizar_categoria(cat_info)

        if solo_con_texto and not info.get("has_text"):
            continue

        if categoria and info["category"] != normalizar_categoria(categoria):
            continue

        try:
            info["mtime"] = md_file.stat().st_mtime
        except Exception:
            info["mtime"] = 0

        tweets.append(info)

    return sorted(tweets, key=lambda x: (x.get("date", "") or "", x.get("mtime", 0)), reverse=True)


def listar_borradores(categoria: Optional[str] = None, toda_la_boveda: bool = False) -> list[dict]:
    """Lista los tweets con estado 'draft'."""
    if toda_la_boveda:
        todos = listar_tweets_boveda(solo_con_texto=True, incluir_archivados=False, categoria=categoria)
        return [t for t in todos if t.get("status") == "draft"]

    archivar_publicados()
    todos = listar_tweets(categoria=categoria, incluir_archivados=False)
    return [t for t in todos if t.get("status") == "draft"]


def obtener_tweet_por_id(tweet_id: str, en_toda_la_boveda: bool = True) -> Optional[dict]:
    """Obtiene un tweet por su ID, stem, filename o título."""
    if not tweet_id or not tweet_id.strip():
        return None

    tweet_id_clean = tweet_id.strip()
    tweet_id_lower = tweet_id_clean.lower()

    if en_toda_la_boveda:
        tweets = listar_tweets_boveda(solo_con_texto=False, incluir_archivados=True)
    else:
        tweets = listar_tweets(incluir_archivados=True)

    # 1. Búsqueda exacta por item_id
    for tweet in tweets:
        if tweet.get("item_id") == tweet_id_clean:
            return tweet

    # 2. Búsqueda exacta por stem o filename
    for tweet in tweets:
        stem = Path(tweet["filepath"]).stem
        fn = tweet.get("filename", "")
        if stem == tweet_id_clean or fn == tweet_id_clean or fn.replace(".md", "") == tweet_id_clean:
            return tweet

    # 3. Búsqueda insensible a mayúsculas
    for tweet in tweets:
        stem = Path(tweet["filepath"]).stem.lower()
        item_id = (tweet.get("item_id") or "").lower()
        filename = tweet.get("filename", "").lower()
        titulo = (tweet.get("titulo") or tweet.get("title") or "").lower()
        if (
            tweet_id_lower in (stem, item_id, filename, filename.replace(".md", ""))
            or tweet_id_lower == titulo
        ):
            return tweet

    # 4. Búsqueda por subcadena en título o stem
    coincidencias = []
    for tweet in tweets:
        stem = Path(tweet["filepath"]).stem.lower()
        titulo = (tweet.get("titulo") or tweet.get("title") or "").lower()
        if tweet_id_lower in stem or tweet_id_lower in titulo:
            coincidencias.append(tweet)

    if len(coincidencias) == 1:
        return coincidencias[0]
    elif len(coincidencias) > 1:
        con_texto = [c for c in coincidencias if c.get("has_text")]
        if len(con_texto) == 1:
            return con_texto[0]
        return coincidencias[0]

    return None


def obtener_tweet_para_publicar(filepath: str) -> Optional[str]:
    """Obtiene el texto del tweet de un archivo."""
    path = _ruta_en_boveda(Path(filepath))
    if not path:
        return None

    try:
        content = path.read_text(encoding="utf-8")
        # Si tiene sección Update, usar esa primero
        update_match = re.search(r"## Update\n\n(.+?)(?=\n## |\n---\n\*Mejorado|\Z)", content, re.DOTALL)
        if update_match:
            return update_match.group(1).strip()

        match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    except Exception:
        return None


def _parsear_frontmatter(filepath: Path) -> Optional[dict]:
    """Parsea el frontmatter y extrae el texto del tweet de un archivo Markdown."""
    try:
        content = filepath.read_text(encoding="utf-8")

        # Archivo sin frontmatter pero markdown válido
        if not content.startswith("---"):
            if filepath.name.startswith((".", "_")):
                return None

            lines = content.strip().split("\n")
            if not lines:
                return None

            info = {
                "filename": filepath.name,
                "filepath": str(filepath),
                "titulo": filepath.stem,
                "status": "draft",
                "source": "manual",
            }

            # Buscar secciones ## Update o ## Tweet si existen
            update_match = re.search(r"## Update\n\n(.+?)(?=\n## |\n---\n\*Mejorado|\Z)", content, re.DOTALL)
            if update_match:
                info["tweet_text"] = update_match.group(1).strip()
                info["has_update"] = True
            else:
                tweet_match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
                if tweet_match:
                    info["tweet_text"] = tweet_match.group(1).strip()
                else:
                    tweet_lines = []
                    started = False
                    for line in lines:
                        if not started:
                            if line.startswith("# "):
                                info["titulo"] = line[2:].strip()
                                continue
                            if line.strip() == "":
                                continue
                            started = True
                        if line.startswith("## "):
                            break
                        tweet_lines.append(line)
                    if tweet_lines:
                        info["tweet_text"] = "\n".join(tweet_lines).strip()
                    else:
                        info["tweet_text"] = content.strip()

            info["tweet_text"] = info.get("tweet_text", "").strip()
            info["char_count"] = len(info["tweet_text"])
            info["has_text"] = bool(info["char_count"] > 0)
            return info

        end_idx = content.find("---", 3)
        if end_idx == -1:
            return None

        frontmatter = content[3:end_idx].strip()
        info = {
            "filename": filepath.name,
            "filepath": str(filepath),
        }

        for line in frontmatter.split("\n"):
            if ":" in line and not line.strip().startswith("-"):
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip().strip('"').strip("'")

        if "title" in info and "titulo" not in info:
            info["titulo"] = info["title"]

        # Intentar extraer texto del tweet
        update_match = re.search(r"## Update\n\n(.+?)(?=\n## |\n---\n\*Mejorado|\Z)", content, re.DOTALL)
        if update_match:
            info["tweet_text"] = update_match.group(1).strip()
            info["has_update"] = True
        else:
            tweet_match = re.search(r"## Tweet\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if tweet_match:
                info["tweet_text"] = tweet_match.group(1).strip()
            else:
                after_frontmatter = content[end_idx + 3:].strip()
                lines = after_frontmatter.split("\n")
                tweet_lines = []
                started = False
                for line in lines:
                    if not started:
                        if line.startswith("# "):
                            info.setdefault("titulo", line[2:].strip())
                            continue
                        if line.strip() == "":
                            continue
                        started = True
                    if line.startswith("## "):
                        break
                    tweet_lines.append(line)

                if tweet_lines:
                    info["tweet_text"] = "\n".join(tweet_lines).strip()

        info["titulo"] = info.get("titulo") or info.get("title") or filepath.stem
        info["item_id"] = info.get("item_id") or filepath.stem
        info["tweet_text"] = info.get("tweet_text", "").strip()
        info["char_count"] = len(info["tweet_text"])
        info["has_text"] = bool(info["char_count"] > 0)

        return info
    except Exception:
        return None


def agregar_update_tweet(filepath: str, tweet_mejorado: str) -> bool:
    """Agrega una sección de update a un tweet existente."""
    path = _ruta_en_boveda(Path(filepath))
    if not path:
        print(f"  ⚠️ Archivo Markdown fuera de la bóveda o no encontrado: {filepath}")
        return False

    try:
        content = path.read_text(encoding="utf-8")
        es_hilo = "\n---\n" in tweet_mejorado
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if es_hilo:
            tweets = tweet_mejorado.split("\n---\n")
            update_content = "## Update\n\n"
            for tweet in tweets:
                update_content += f"{tweet.strip()}\n\n---\n\n"
            update_content += f"*Mejorado el {now}*\n\n"
        else:
            update_content = f"## Update\n\n{tweet_mejorado}\n\n---\n*Mejorado el {now}*\n\n"

        if "## Update" in content:
            pattern = r"## Update.*?(?=\n## |$)"
            content = re.sub(pattern, update_content, content, flags=re.DOTALL)
        else:
            if "## Revisión" in content:
                content = content.replace("## Revisión", f"{update_content}## Revisión")
            else:
                content += f"\n\n{update_content}"

        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  ⚠️ Error agregando update: {e}")
        return False


def obtener_estadisticas() -> dict:
    """Obtiene estadísticas generales y por categoría de la bóveda."""
    archivar_publicados()
    todos = listar_tweets(incluir_archivados=True)

    stats = {
        "total_tweets": len(todos),
        "borradores": len([t for t in todos if t.get("status") == "draft"]),
        "publicados": len([t for t in todos if t.get("is_archived") or t.get("status") in ("published", "publicado")]),
        "por_categoria": {
            "teclado": len([t for t in todos if t.get("category") == "teclado" and not t.get("is_archived")]),
            "github": len([t for t in todos if t.get("category") == "github" and not t.get("is_archived")]),
            "news": len([t for t in todos if t.get("category") == "news" and not t.get("is_archived")]),
            "codigo": len([t for t in todos if t.get("category") == "codigo" and not t.get("is_archived")]),
            "archivados": len([t for t in todos if t.get("is_archived")]),
        },
    }
    return stats
