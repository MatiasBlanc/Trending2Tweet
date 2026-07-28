"""Generador de tarjetas visuales para tweets.

Diseño: Tokyo Night color palette
Tipografía:
  - Doto      → Números y estadísticas (estilo tech/dot-matrix)
  - Montserrat → Títulos, descripciones, badges y branding (alta legibilidad)

Variables de entorno:
  ENABLE_TWEET_IMAGES   true/false  (default: true)
  CARD_BRAND_NAME       texto       (default: "matiasblnc")
"""

import os
import math
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────
CARD_BRAND_NAME     = os.getenv("CARD_BRAND_NAME", "matiasblnc")
ENABLE_TWEET_IMAGES = os.getenv("ENABLE_TWEET_IMAGES", "true").lower() == "true"

# ── Rutas de fuentes (bundled en assets/fonts/) ───────────────────
_BASE = Path(__file__).parent / "assets" / "fonts"

_DOTO_REGULAR  = str(_BASE / "Doto-400.ttf")
_DOTO_BOLD     = str(_BASE / "Doto-700.ttf")
_DOTO_BLACK    = str(_BASE / "Doto-900.ttf")

_MONT_REGULAR  = str(_BASE / "Montserrat-Regular.ttf")
_MONT_SEMIBOLD = str(_BASE / "Montserrat-SemiBold.ttf")
_MONT_BOLD     = str(_BASE / "Montserrat-Bold.ttf")
_MONT_EXTRABOLD= str(_BASE / "Montserrat-ExtraBold.ttf")
_MONT_BLACK    = str(_BASE / "Montserrat-Black.ttf")

# ── Dimensiones ───────────────────────────────────────────────────
W, H    = 1600, 900
PANEL_M = 56
PADDING = 72

# ══════════════════════════════════════════════════════════════════
# TOKYO NIGHT PALETTE
# ══════════════════════════════════════════════════════════════════
TN_BG        = (26,  27,  38)   # #1a1b26  fondo principal
TN_BG_DARK   = (22,  22,  30)   # #16161e  fondo más oscuro
TN_BG_PANEL  = (36,  40,  59)   # #24283b  panel bg
TN_BG_HL     = (41,  46,  66)   # #292e42  borde
TN_FG        = (192, 202, 245)  # #c0caf5  texto principal
TN_COMMENT   = (86,  95,  137)  # #565f89  texto secundario
TN_BLUE      = (122, 162, 247)  # #7aa2f7  azul tokyo
TN_BLUE_DIM  = (30,  32,  60)   # fondo badge azul
TN_CYAN      = (125, 207, 255)  # #7dcfff  cyan
TN_GREEN     = (158, 206, 106)  # #9ece6a  verde
TN_PURPLE    = (187, 154, 247)  # #bb9af7  purple
TN_ORANGE    = (255, 158, 100)  # #ff9e64  naranja
TN_ORANGE_DIM= (50,  30,  12)   # fondo badge naranja
TN_YELLOW    = (224, 175, 104)  # #e0af68  amarillo (stars)
TN_RED       = (247, 118, 142)  # #f7768e  rojo


# ── Helpers ───────────────────────────────────────────────────────

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Carga fuente con fallback a Pillow default."""
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def _gradient(draw: ImageDraw.ImageDraw, w: int, h: int,
               top: tuple, bottom: tuple) -> None:
    """Gradiente vertical."""
    for y in range(h):
        t = y / h
        r = int(top[0] * (1-t) + bottom[0] * t)
        g = int(top[1] * (1-t) + bottom[1] * t)
        b = int(top[2] * (1-t) + bottom[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _wrap(text: str, font: ImageFont.FreeTypeFont,
          max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Wrap de texto al ancho máximo."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if (draw.textbbox((0,0), test, font=font)[2]) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _tw(draw, text, font):
    """Text width."""
    return draw.textbbox((0,0), text, font=font)[2]


def _th(draw, text, font):
    """Text height."""
    b = draw.textbbox((0,0), text, font=font)
    return b[3] - b[1]


def _stars_str(stars: int) -> str:
    return f"{stars/1000:.1f}k" if stars >= 1000 else str(stars)


def _badge(draw, x, y, text, font, fg, bg, border, radius=20):
    """Dibuja un badge pill con texto perfectamente alineado en el centro."""
    bb = draw.textbbox((0, 0), text, font=font)
    text_w = bb[2] - bb[0]
    text_h = bb[3] - bb[1]
    
    # Padding interno
    padding_x = 24
    padding_y = 12
    
    pw = text_w + padding_x * 2
    ph = text_h + padding_y * 2
    
    # Dibujar la cápsula
    draw.rounded_rectangle([x, y, x + pw, y + ph], radius=radius,
                            fill=bg, outline=border, width=1)
    
    # Centrar horizontal y verticalmente usando anchor="mm" (middle-middle)
    center_x = x + (pw / 2)
    center_y = y + (ph / 2)
    draw.text((center_x, center_y), text, font=font, fill=fg, anchor="mm")
    
    return pw, ph


def _draw_star_vector(draw, cx, cy, size, fill_color):
    """Dibuja geométricamente una estrella de 5 puntas perfecta sin depender de fuentes unicode."""
    points = []
    r_outer = size
    r_inner = size * 0.40
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill_color)


# ══════════════════════════════════════════════════════════════════
# TARJETA GITHUB  —  acento azul Tokyo Night
# ══════════════════════════════════════════════════════════════════

def generate_github_card(
    repo_name: str,
    description: str,
    language: str,
    stars: int,
    output_path: Optional[str] = None,
) -> bytes | None:
    """Genera tarjeta visual para un repo de GitHub (Tokyo Night)."""
    if not ENABLE_TWEET_IMAGES:
        return None

    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Fondo degradado
    _gradient(draw, W, H, TN_BG_DARK, TN_BG)

    # Panel central
    draw.rounded_rectangle(
        [PANEL_M, PANEL_M, W-PANEL_M, H-PANEL_M],
        radius=20, fill=TN_BG_PANEL, outline=TN_BG_HL, width=1,
    )

    # Barra de acento izquierda (azul tokyo)
    draw.rounded_rectangle(
        [PANEL_M, PANEL_M+40, PANEL_M+4, H-PANEL_M-40],
        radius=2, fill=TN_BLUE,
    )

    # Fuentes:
    # Montserrat para badges, nombres, textos y branding (alineación impecable)
    # Doto para estadísticas y números (dot-matrix aesthetic)
    f_badge_m  = _font(_MONT_BLACK,     20)   # Badge usando Montserrat para mejor alineación
    f_owner_m  = _font(_MONT_SEMIBOLD,  28)   # "owner /"
    f_repo_m   = _font(_MONT_BLACK,     62)   # nombre del repo
    f_desc_m   = _font(_MONT_REGULAR,   33)   # descripción
    f_stars_d  = _font(_DOTO_BLACK,     68)   # número stars en Doto
    f_label_m  = _font(_MONT_SEMIBOLD,  22)   # "STARS", "LANGUAGE"
    f_brand_m  = _font(_MONT_BOLD,      30)   # Branding en Montserrat y más grande

    cx = PANEL_M + PADDING
    cw = W - cx*2

    # ── Badge "GITHUB TRENDING" ──────────────────────────────────
    by = PANEL_M + 48
    bw, bh = _badge(draw, cx, by, "GITHUB TRENDING",
                    f_badge_m, TN_BLUE, TN_BLUE_DIM, TN_BLUE, radius=12)

    # ── Owner / Repo ─────────────────────────────────────────────
    parts = repo_name.split("/", 1)
    oy = by + bh + 32

    if len(parts) == 2:
        draw.text((cx, oy), parts[0] + " /", font=f_owner_m, fill=TN_COMMENT)
        oy += _th(draw, parts[0], f_owner_m) + 8
        repo_str = parts[1]
    else:
        repo_str = repo_name

    draw.text((cx, oy), repo_str, font=f_repo_m, fill=TN_FG)
    oy += _th(draw, repo_str, f_repo_m) + 24

    # ── Separador ─────────────────────────────────────────────────
    draw.line([(cx, oy), (W-cx, oy)], fill=TN_BG_HL, width=1)
    oy += 24

    # ── Descripción ───────────────────────────────────────────────
    if len(description) > 100:
        description = description[:100].rsplit(" ", 1)[0] + "…"
    for line in _wrap(description, f_desc_m, cw, draw)[:2]:
        draw.text((cx, oy), line, font=f_desc_m, fill=TN_FG)
        oy += _th(draw, line, f_desc_m) + 8

    # ── Stats (sección inferior) ──────────────────────────────────
    sy = H - PANEL_M - PADDING - 88
    draw.line([(cx, sy-16), (W-cx, sy-16)], fill=TN_BG_HL, width=1)

    # Stars (Dibuja estrella vector + número en Doto)
    star_radius = 28
    star_cx = cx + star_radius
    star_cy = sy + 30
    _draw_star_vector(draw, star_cx, star_cy, star_radius, TN_YELLOW)
    
    stars_s = _stars_str(stars)
    # Dibujamos el número con un pequeño offset respecto a la estrella
    draw.text((cx + star_radius * 2 + 16, sy), stars_s, font=f_stars_d, fill=TN_FG)
    total_sw = star_radius * 2 + 16 + _tw(draw, stars_s, f_stars_d)
    
    # Label "STARS"
    draw.text((cx, sy + 68), "STARS", font=f_label_m, fill=TN_COMMENT)

    # Language badge (Montserrat)
    if language:
        lx = cx + total_sw + 48
        _badge(draw, lx, sy + 10, language.upper(),
               f_label_m, TN_CYAN, TN_BG_HL, TN_CYAN, radius=8)

    # Branding (Montserrat grande y azul Tokyo Night)
    brand = "@" + CARD_BRAND_NAME
    bw2 = _tw(draw, brand, f_brand_m)
    draw.text((W - PANEL_M - PADDING - bw2, sy + 18),
              brand, font=f_brand_m, fill=TN_BLUE)

    # ── Guardar ───────────────────────────────────────────────────
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    if output_path:
        img.save(output_path, format="PNG", optimize=True)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# TARJETA NEWS  —  acento naranja Tokyo Night
# ══════════════════════════════════════════════════════════════════

def generate_news_card(
    title: str,
    score: int,
    comments: int,
    author: str = "",
    output_path: Optional[str] = None,
) -> bytes | None:
    """Genera tarjeta visual para una noticia de Hacker News (Tokyo Night)."""
    if not ENABLE_TWEET_IMAGES:
        return None

    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Fondo degradado
    _gradient(draw, W, H, TN_BG_DARK, TN_BG)

    # Panel central
    draw.rounded_rectangle(
        [PANEL_M, PANEL_M, W-PANEL_M, H-PANEL_M],
        radius=20, fill=TN_BG_PANEL, outline=TN_BG_HL, width=1,
    )

    # Barra acento izquierda (naranja tokyo)
    draw.rounded_rectangle(
        [PANEL_M, PANEL_M+40, PANEL_M+4, H-PANEL_M-40],
        radius=2, fill=TN_ORANGE,
    )

    # Fuentes
    f_badge_m  = _font(_MONT_BLACK,     20)
    f_score_d  = _font(_DOTO_BLACK,     68)
    f_comm_d   = _font(_DOTO_BOLD,      42)
    f_title_m  = _font(_MONT_BLACK,     52)
    f_title2_m = _font(_MONT_BLACK,     42)
    f_label_m  = _font(_MONT_SEMIBOLD,  22)
    f_author_m = _font(_MONT_REGULAR,   26)
    f_brand_m  = _font(_MONT_BOLD,      30)

    cx = PANEL_M + PADDING
    cw = W - cx*2

    # ── Badge "HN TRENDING" ──────────────────────────────────────
    by = PANEL_M + 48
    bw, bh = _badge(draw, cx, by, "HN TRENDING",
                    f_badge_m, TN_ORANGE, TN_ORANGE_DIM, TN_ORANGE, radius=12)

    # ── Título ────────────────────────────────────────────────────
    ty = by + bh + 32
    ft = f_title2_m if len(title) > 75 else f_title_m
    for line in _wrap(title, ft, cw, draw)[:3]:
        draw.text((cx, ty), line, font=ft, fill=TN_FG)
        ty += _th(draw, line, ft) + 8

    # ── Autor ─────────────────────────────────────────────────────
    if author:
        ty += 8
        draw.line([(cx, ty), (cx + 200, ty)], fill=TN_BG_HL, width=1)
        ty += 12
        draw.text((cx, ty), f"by {author}", font=f_author_m, fill=TN_COMMENT)

    # ── Stats ─────────────────────────────────────────────────────
    sy = H - PANEL_M - PADDING - 88
    draw.line([(cx, sy-16), (W-cx, sy-16)], fill=TN_BG_HL, width=1)

    # Score (Doto — naranja)
    score_s = str(score)
    draw.text((cx, sy), score_s, font=f_score_d, fill=TN_ORANGE)
    sw = _tw(draw, score_s, f_score_d)
    draw.text((cx, sy + 68), "PUNTOS HN", font=f_label_m, fill=TN_COMMENT)

    # Barra de score
    bar_x  = cx + sw + 40
    bar_mw = 260
    fill_w = int(bar_mw * min(score / 2000, 1.0))
    draw.rounded_rectangle([bar_x, sy+16, bar_x+bar_mw, sy+24],
                            radius=4, fill=TN_BG_HL)
    if fill_w > 0:
        draw.rounded_rectangle([bar_x, sy+16, bar_x+fill_w, sy+24],
                                radius=4, fill=TN_ORANGE)

    # Comentarios (Doto — cyan)
    comm_s = str(comments)
    cx2 = bar_x + bar_mw + 48
    draw.text((cx2, sy), comm_s, font=f_comm_d, fill=TN_CYAN)
    draw.text((cx2, sy + 52), "COMMENTS", font=f_label_m, fill=TN_COMMENT)

    # Branding (Montserrat grande y naranja Tokyo Night)
    brand = "@" + CARD_BRAND_NAME
    bw2 = _tw(draw, brand, f_brand_m)
    draw.text((W - PANEL_M - PADDING - bw2, sy + 18),
              brand, font=f_brand_m, fill=TN_ORANGE)

    # ── Guardar ───────────────────────────────────────────────────
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    if output_path:
        img.save(output_path, format="PNG", optimize=True)
    return buf.getvalue()


# ── Test local ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generando tarjeta GitHub (Tokyo Night)...")
    generate_github_card(
        repo_name="microsoft/TypeScript",
        description="TypeScript is a superset of JavaScript that compiles to clean JavaScript output.",
        language="TypeScript",
        stars=102400,
        output_path="/tmp/preview_github.png",
    )
    print("  ✅ /tmp/preview_github.png")

    print("Generando tarjeta News (Tokyo Night)...")
    generate_news_card(
        title="Mistral releases new open model that beats GPT-4 on coding benchmarks",
        score=1842,
        comments=347,
        author="mistral_ai",
        output_path="/tmp/preview_news.png",
    )
    print("  ✅ /tmp/preview_news.png")
