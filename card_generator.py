"""Generador de tarjetas visuales para tweets.

Genera imágenes 1600x900px (ratio 16:9 óptimo para X/Twitter)
con diseño premium dark mode. Una tarjeta por tipo de contenido:
  - GitHub: stats del repo con acento azul tech
  - News: headline con acento naranja Hacker News

Usa solo Pillow + fuentes del sistema (sin dependencias extra).
Compatible con Railway sin configuración adicional.

Variables de entorno disponibles:
  CARD_BRAND_NAME     Nombre en la esquina inferior (default: "trending2tweet")
  ENABLE_TWEET_IMAGES true/false — desactivar sin tocar código (default: true)
"""

import glob
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import config

# ── Config desde variables de entorno ────────────────────────────
CARD_BRAND_NAME     = os.getenv("CARD_BRAND_NAME", "trending2tweet")
ENABLE_TWEET_IMAGES = os.getenv("ENABLE_TWEET_IMAGES", "true").lower() == "true"

# ── Búsqueda resiliente de fuentes ───────────────────────────────
# Busca en múltiples paths (local Fedora/Debian, Railway/Nix, Alpine)

_SANS_REGULAR_PATHS = [
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]
_SANS_BOLD_PATHS = [
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]
_MONO_PATHS = [
    "/usr/share/fonts/adobe-source-code-pro-fonts/SourceCodePro-Regular.otf",
    "/usr/share/fonts/opentype/source-code-pro/SourceCodePro-Regular.otf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf",
]
_MONO_BOLD_PATHS = [
    "/usr/share/fonts/adobe-source-code-pro-fonts/SourceCodePro-Bold.otf",
    "/usr/share/fonts/opentype/source-code-pro/SourceCodePro-Bold.otf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Bold.ttf",
]


def _find_font(paths: list[str]) -> str | None:
    """Retorna la primera fuente disponible en la lista de paths."""
    for p in paths:
        if "*" in p:
            matches = glob.glob(p)
            if matches:
                return matches[0]
        elif Path(p).exists():
            return p
    return None


_FONT_SANS_REGULAR = _find_font(_SANS_REGULAR_PATHS)
_FONT_SANS_BOLD    = _find_font(_SANS_BOLD_PATHS)
_FONT_MONO         = _find_font(_MONO_PATHS)
_FONT_MONO_BOLD    = _find_font(_MONO_BOLD_PATHS)

# ── Dimensiones ───────────────────────────────────────────────────
W, H    = 1600, 900   # 16:9 — óptimo para X/Twitter
PADDING = 80
PANEL_M = 60          # margen del panel central

# ── Paleta GitHub card ────────────────────────────────────────────
GH_BG_TOP     = (10,  14,  20)
GH_BG_BOTTOM  = (18,  24,  38)
GH_ACCENT     = (88,  166, 255)
GH_ACCENT_DIM = (33,  60,  96)
GH_TEXT       = (230, 237, 243)
GH_MUTED      = (110, 118, 129)
GH_CARD_BG    = (22,  27,  34)
GH_BORDER     = (48,  54,  61)

# ── Paleta News card ──────────────────────────────────────────────
NW_BG_TOP     = (14,  10,  8)
NW_BG_BOTTOM  = (26,  18,  12)
NW_ACCENT     = (255, 102, 0)
NW_ACCENT_DIM = (80,  32,  0)
NW_TEXT       = (240, 234, 228)
NW_MUTED      = (140, 120, 100)
NW_CARD_BG    = (28,  22,  16)
NW_BORDER     = (60,  46,  32)


# ── Helpers ───────────────────────────────────────────────────────

def _load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    """Carga fuente TTF/OTF con fallback al default de Pillow."""
    if path:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _gradient(draw: ImageDraw.ImageDraw, w: int, h: int,
               top: tuple, bottom: tuple) -> None:
    """Gradiente vertical suave."""
    for y in range(h):
        t = y / h
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _wrap(text: str, font: ImageFont.FreeTypeFont,
          max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Envuelve texto al ancho máximo."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _stars_str(stars: int) -> str:
    return f"{stars / 1000:.1f}k" if stars >= 1000 else str(stars)


# ═══════════════════════════════════════════════════════════════
# TARJETA GITHUB
# ═══════════════════════════════════════════════════════════════

def generate_github_card(
    repo_name: str,
    description: str,
    language: str,
    stars: int,
    output_path: Optional[str] = None,
) -> bytes | None:
    """Genera tarjeta visual para un repo de GitHub.

    Returns None si ENABLE_TWEET_IMAGES es false.
    """
    if not ENABLE_TWEET_IMAGES:
        return None

    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    _gradient(draw, W, H, GH_BG_TOP, GH_BG_BOTTOM)

    # Dots grid decorativo
    for gx in range(0, W, 48):
        for gy in range(0, H, 48):
            draw.point((gx, gy), fill=(255, 255, 255))

    # Panel central
    draw.rounded_rectangle(
        [PANEL_M, PANEL_M, W - PANEL_M, H - PANEL_M],
        radius=24, fill=GH_CARD_BG, outline=GH_BORDER, width=1,
    )

    # Barra acento top
    cx = PANEL_M + PADDING
    draw.rounded_rectangle(
        [cx, PANEL_M + 1, cx + 180, PANEL_M + 5],
        radius=2, fill=GH_ACCENT,
    )

    # Fuentes
    f_badge = _load_font(_FONT_SANS_BOLD,    22)
    f_owner = _load_font(_FONT_MONO,         28)
    f_repo  = _load_font(_FONT_SANS_BOLD,    54)
    f_desc  = _load_font(_FONT_SANS_REGULAR, 34)
    f_stat  = _load_font(_FONT_SANS_BOLD,    40)
    f_label = _load_font(_FONT_SANS_REGULAR, 24)
    f_brand = _load_font(_FONT_SANS_BOLD,    24)

    cw = W - cx * 2   # ancho del contenido

    # Badge "GitHub Trending"
    by = PANEL_M + 50
    btxt = "  ⭐ GitHub Trending  "
    bb = draw.textbbox((0, 0), btxt, font=f_badge)
    bw = bb[2] - bb[0] + 20
    draw.rounded_rectangle([cx, by, cx + bw, by + 36], radius=18,
                            fill=GH_ACCENT_DIM, outline=GH_ACCENT, width=1)
    draw.text((cx + 10, by + 7), btxt, font=f_badge, fill=GH_ACCENT)

    # Owner / Repo
    parts = repo_name.split("/", 1)
    oy = by + 36 + 28
    if len(parts) == 2:
        draw.text((cx, oy), parts[0] + " /", font=f_owner, fill=GH_MUTED)
        oy += 34
        draw.text((cx, oy), parts[1], font=f_repo, fill=GH_TEXT)
        rb = draw.textbbox((0, 0), parts[1], font=f_repo)
    else:
        draw.text((cx, oy), repo_name, font=f_repo, fill=GH_TEXT)
        rb = draw.textbbox((0, 0), repo_name, font=f_repo)
    oy += (rb[3] - rb[1]) + 28

    # Separador
    draw.line([(cx, oy), (W - cx, oy)], fill=GH_BORDER, width=1)
    oy += 28

    # Descripción (máx 90 chars, 3 líneas)
    if len(description) > 90:
        description = description[:90].rsplit(" ", 1)[0] + "…"
    for line in _wrap(description, f_desc, cw, draw)[:3]:
        draw.text((cx, oy), line, font=f_desc, fill=GH_TEXT)
        lb = draw.textbbox((0, 0), line, font=f_desc)
        oy += (lb[3] - lb[1]) + 10

    # Stats en la zona inferior
    sy = H - PANEL_M - PADDING - 100
    draw.line([(cx, sy - 20), (W - cx, sy - 20)], fill=GH_BORDER, width=1)

    # Stars
    draw.text((cx, sy), "★", font=f_stat, fill="#F0B429")
    swb = draw.textbbox((0, 0), "★", font=f_stat)
    sw  = swb[2] - swb[0]
    stars_s = _stars_str(stars)
    draw.text((cx + sw + 8, sy), stars_s, font=f_stat, fill=GH_TEXT)
    draw.text((cx, sy + 48), "stars", font=f_label, fill=GH_MUTED)
    full_sw = sw + 8 + (draw.textbbox((0,0), stars_s, font=f_stat)[2])

    # Language pill
    if language:
        lx = cx + full_sw + 48
        ltxt = f"  {language}  "
        lb2  = draw.textbbox((0, 0), ltxt, font=f_badge)
        lw2  = lb2[2] - lb2[0] + 16
        draw.rounded_rectangle([lx, sy + 5, lx + lw2, sy + 44],
                                radius=20, fill=GH_ACCENT_DIM,
                                outline=GH_ACCENT, width=1)
        draw.text((lx + 8, sy + 12), ltxt, font=f_badge, fill=GH_ACCENT)

    # Branding
    brand_b = draw.textbbox((0, 0), CARD_BRAND_NAME, font=f_brand)
    draw.text(
        (W - PANEL_M - PADDING - (brand_b[2] - brand_b[0]), sy + 12),
        CARD_BRAND_NAME, font=f_brand, fill=GH_MUTED,
    )

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    if output_path:
        img.save(output_path, format="PNG", optimize=True)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════
# TARJETA NEWS
# ═══════════════════════════════════════════════════════════════

def generate_news_card(
    title: str,
    score: int,
    comments: int,
    author: str = "",
    output_path: Optional[str] = None,
) -> bytes | None:
    """Genera tarjeta visual para una noticia de Hacker News.

    Returns None si ENABLE_TWEET_IMAGES es false.
    """
    if not ENABLE_TWEET_IMAGES:
        return None

    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    _gradient(draw, W, H, NW_BG_TOP, NW_BG_BOTTOM)

    draw.rounded_rectangle(
        [PANEL_M, PANEL_M, W - PANEL_M, H - PANEL_M],
        radius=24, fill=NW_CARD_BG, outline=NW_BORDER, width=1,
    )

    cx = PANEL_M + PADDING
    draw.rounded_rectangle(
        [cx, PANEL_M + 1, cx + 160, PANEL_M + 5],
        radius=2, fill=NW_ACCENT,
    )

    # Fuentes
    f_badge  = _load_font(_FONT_SANS_BOLD,    22)
    f_title  = _load_font(_FONT_SANS_BOLD,    54)
    f_title2 = _load_font(_FONT_SANS_BOLD,    44)
    f_label  = _load_font(_FONT_SANS_REGULAR, 26)
    f_stat   = _load_font(_FONT_SANS_BOLD,    52)
    f_stat2  = _load_font(_FONT_SANS_BOLD,    36)
    f_brand  = _load_font(_FONT_SANS_BOLD,    24)

    cw = W - cx * 2

    # Badge "Trending on HN"
    by   = PANEL_M + 50
    btxt = "  🔥 Trending on Hacker News  "
    bb   = draw.textbbox((0, 0), btxt, font=f_badge)
    bw   = bb[2] - bb[0] + 20
    draw.rounded_rectangle([cx, by, cx + bw, by + 36], radius=18,
                            fill=NW_ACCENT_DIM, outline=NW_ACCENT, width=1)
    draw.text((cx + 10, by + 7), btxt, font=f_badge, fill=NW_ACCENT)

    # Título
    ty = by + 36 + 36
    ft = f_title2 if len(title) > 80 else f_title
    for line in _wrap(title, ft, cw, draw)[:3]:
        draw.text((cx, ty), line, font=ft, fill=NW_TEXT)
        lb = draw.textbbox((0, 0), line, font=ft)
        ty += (lb[3] - lb[1]) + 10

    # Autor
    sep_y = ty + 20
    draw.line([(cx, sep_y), (W - cx, sep_y)], fill=NW_BORDER, width=1)
    if author:
        draw.text((cx, sep_y + 16), f"by {author}", font=f_label, fill=NW_MUTED)

    # Stats
    sy = H - PANEL_M - PADDING - 110
    draw.line([(cx, sy - 20), (W - cx, sy - 20)], fill=NW_BORDER, width=1)

    # Score
    ss = str(score)
    draw.text((cx, sy), ss, font=f_stat, fill=NW_ACCENT)
    sb  = draw.textbbox((0, 0), ss, font=f_stat)
    sw  = sb[2] - sb[0]
    draw.text((cx, sy + 58), "puntos HN", font=f_label, fill=NW_MUTED)

    # Barra de score
    bar_x   = cx + sw + 40
    bar_mw  = 280
    bar_fill = min(score / 2000, 1.0)
    draw.rounded_rectangle([bar_x, sy + 10, bar_x + bar_mw, sy + 20],
                            radius=5, fill=NW_ACCENT_DIM)
    if bar_fill > 0:
        draw.rounded_rectangle(
            [bar_x, sy + 10, bar_x + int(bar_mw * bar_fill), sy + 20],
            radius=5, fill=NW_ACCENT,
        )

    # Comentarios
    cs = str(comments)
    cx2 = bar_x + bar_mw + 50
    draw.text((cx2, sy), cs, font=f_stat2, fill=NW_TEXT)
    draw.text((cx2, sy + 46), "comentarios", font=f_label, fill=NW_MUTED)

    # Branding
    brand_b = draw.textbbox((0, 0), CARD_BRAND_NAME, font=f_brand)
    draw.text(
        (W - PANEL_M - PADDING - (brand_b[2] - brand_b[0]), sy + 12),
        CARD_BRAND_NAME, font=f_brand, fill=NW_MUTED,
    )

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    if output_path:
        img.save(output_path, format="PNG", optimize=True)
    return buf.getvalue()


# ── Test local ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generando tarjeta GitHub...")
    generate_github_card(
        repo_name="microsoft/TypeScript",
        description="TypeScript is a superset of JavaScript that compiles to clean JavaScript output.",
        language="TypeScript",
        stars=102400,
        output_path="/tmp/preview_github.png",
    )
    print("  ✅ /tmp/preview_github.png")

    print("Generando tarjeta News...")
    generate_news_card(
        title="Mistral releases new open model that beats GPT-4 on coding benchmarks",
        score=1842,
        comments=347,
        author="mistral_ai",
        output_path="/tmp/preview_news.png",
    )
    print("  ✅ /tmp/preview_news.png")
