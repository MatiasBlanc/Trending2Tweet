"""Bot de noticias sobre programación y desarrollo de software.

Uso: python -m bots.codigo
"""

from src.topic_news import ejecutar_bot_tematico

PROMPT_FILE = "prompts/prompt_codigo.txt"

KEYWORDS = (
    "code",
    "coding",
    "programming",
    "programming language",
    "software",
    "developer",
    "developers",
    "compiler",
    "interpreter",
    "open source",
    "github",
    "git",
    "python",
    "javascript",
    "typescript",
    "rust",
    "golang",
    "java",
    "react",
    "linux",
    "terminal",
    "cli",
    "api",
    "database",
    "docker",
    "kubernetes",
    "vscode",
    "neovim",
    "vim",
    "emacs",
)

ESTILO_GANCHO = (
    "Enfócate en la consecuencia práctica para quien escribe y mantiene software. "
    "Contrasta la promesa de la noticia con el trabajo real de un desarrollador."
)


def main() -> None:
    """Ejecuta el bot de noticias de programación."""
    ejecutar_bot_tematico(
        nombre_bot="codigo",
        nombre_visible="Code News Bot",
        prompt_file=PROMPT_FILE,
        keywords=KEYWORDS,
        estilo_gancho=ESTILO_GANCHO,
    )


if __name__ == "__main__":
    main()
