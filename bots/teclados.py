"""Bot de noticias sobre teclados y periféricos para escribir.

Uso: python -m bots.teclados
"""

from src.topic_news import ejecutar_bot_tematico

PROMPT_FILE = "prompts/prompt_teclados.txt"

KEYWORDS = (
    "keyboard",
    "keyboards",
    "mechanical keyboard",
    "split keyboard",
    "ergonomic keyboard",
    "teclado",
    "keycap",
    "keycaps",
    "switches",
    "qmk",
    "via keyboard",
    "keyboard firmware",
    "keyboard layout",
    "colemak",
    "dvorak",
    "touch typing",
    "stenography",
)

ESTILO_GANCHO = (
    "Enfócate en cómo la noticia cambia la experiencia de escribir, la ergonomía "
    "o la personalización. Evita tratar el teclado como un simple accesorio."
)


def main() -> None:
    """Ejecuta el bot de noticias sobre teclados."""
    ejecutar_bot_tematico(
        nombre_bot="teclados",
        nombre_visible="Keyboard News Bot",
        prompt_file=PROMPT_FILE,
        keywords=KEYWORDS,
        estilo_gancho=ESTILO_GANCHO,
    )


if __name__ == "__main__":
    main()
