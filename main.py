#!/usr/bin/env python3
"""Trending2Tweet: menú interactivo y punto de entrada para los bots."""

import importlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from src import config
from src.obsidian_vault import listar_borradores, obtener_estadisticas
from src.publishing import publicar_y_archivar_borrador

ANCHO_MENU = 76
MAX_GENERACION = config.MAX_GENERATION_LIMIT
OPCIONES_SALIDA = ("0", "q", "quit", "exit", "salir")
RESPUESTAS_AFIRMATIVAS = ("s", "si", "sí", "y", "yes")

OPCIONES_GENERACION = (
    ("1", "🐙", "GitHub Trending", "repositorios nuevos con más actividad"),
    ("2", "🐙", "GitHub Manual", "analizar un repositorio concreto"),
    ("3", "📰", "Tech News", "noticias tecnológicas de Hacker News"),
    ("4", "💻", "Code News", "historias y aprendizajes de programación"),
    ("5", "🧩", "Retos de Código", "desafíos por lenguaje y dificultad"),
    ("6", "⌨️ ", "Teclados", "publicaciones de periféricos desde Reddit"),
)

OPCIONES_GESTION = (
    ("7", "✨", "Mejorar Tweet", "pulir un tweet de la bóveda con IA"),
    ("8", "📦", "Archivar", "mover publicaciones marcadas como publicadas"),
    ("9", "🚀", "Publicar en X", "publicar un borrador después de revisarlo"),
    ("10", "📊", "Estadísticas", "ver el estado de la bóveda"),
)


def _estilizar(texto: str, codigo: str) -> str:
    """Aplica color ANSI cuando la salida es interactiva y lo permite."""
    if not sys.stdout.isatty() or os.getenv("NO_COLOR"):
        return texto
    return f"\033[{codigo}m{texto}\033[0m"


def _titulo(texto: str) -> str:
    """Devuelve un título destacado para las secciones del menú."""
    return _estilizar(texto, "1;36")


def _ruta_visible(ruta: str, maximo: int = 58) -> str:
    """Acorta una ruta larga sin ocultar su último componente."""
    ruta_expandida = str(Path(ruta).expanduser())
    if len(ruta_expandida) <= maximo:
        return ruta_expandida
    return f"…{ruta_expandida[-(maximo - 1):]}"


def banner() -> None:
    """Muestra la cabecera del panel interactivo."""
    borde = _estilizar("╭" + "─" * (ANCHO_MENU - 2) + "╮", "1;36")
    cierre = _estilizar("╰" + "─" * (ANCHO_MENU - 2) + "╯", "1;36")
    print(borde)
    print("│" + _estilizar("  🤖  TRENDING2TWEET", "1;37") + " " * (ANCHO_MENU - 24) + "│")
    print("│" + "  Panel de creación y revisión de contenido para Obsidian" + " " * 15 + "│")
    ruta = _ruta_visible(config.OBSIDIAN_VAULT_PATH)
    relleno = max(1, ANCHO_MENU - len(ruta) - 20)
    print("│" + _estilizar(f"  📂 Bóveda: {ruta}", "2") + " " * relleno + "│")
    print(cierre)


def _mostrar_opciones(opciones: tuple[tuple[str, str, str, str], ...]) -> None:
    """Muestra un grupo de opciones con formato alineado."""
    for numero, icono, nombre, descripcion in opciones:
        etiqueta = f"{numero:>2}. {icono} {nombre:<18}"
        print(f"  {_estilizar(etiqueta, '1;37')}  {_estilizar(descripcion, '2')}")


def mostrar_menu() -> None:
    """Muestra las opciones agrupadas del menú principal."""
    print()
    print(_titulo("  ✦ CREAR CONTENIDO"))
    _mostrar_opciones(OPCIONES_GENERACION)
    print()
    print(_titulo("  ✦ REVISAR Y GESTIONAR"))
    _mostrar_opciones(OPCIONES_GESTION)
    print()
    print(f"  {_estilizar(' 0.', '1;31')} 👋 Salir")
    print(_estilizar("  Atajos: q salir · Ctrl+C cancelar una operación", "2"))


def _leer_cantidad(mensaje: str = "¿Cuántos borradores deseas generar? [1]: ") -> int:
    """Solicita una cantidad segura dentro del límite permitido.

    Args:
        mensaje: Texto que se muestra al pedir la cantidad.

    Returns:
        Cantidad entre 1 y ``MAX_GENERACION``.
    """
    while True:
        valor = input(f"  {mensaje}").strip()
        if not valor:
            return 1
        if valor.isdigit() and 1 <= int(valor) <= MAX_GENERACION:
            return int(valor)
        print(f"  ⚠️ Introduce un número entre 1 y {MAX_GENERACION}.")


def _confirmar(mensaje: str) -> bool:
    """Solicita una confirmación explícita al usuario."""
    respuesta = input(f"\n  {mensaje} (s/n): ").strip().lower()
    return respuesta in RESPUESTAS_AFIRMATIVAS


def _pausar() -> None:
    """Espera a que el usuario termine de revisar el resultado de una acción."""
    try:
        input(_estilizar("\n  Presiona Enter para volver al menú…", "2"))
    except (KeyboardInterrupt, EOFError):
        print()


def _ejecutar_bot(
    nombre: str, argumentos: list[str], capturar_errores: bool = True
) -> None:
    """Ejecuta un bot desde el menú sin perder el estado de la aplicación.

    Args:
        nombre: Nombre del módulo dentro del paquete ``bots``.
        argumentos: Argumentos que el bot recibiría desde la línea de comandos.
        capturar_errores: Mantiene el menú abierto cuando la acción falla.
    """
    modulo: ModuleType = importlib.import_module(f"bots.{nombre}")
    argv_original = sys.argv[:]
    try:
        sys.argv = [nombre, *argumentos]
        ejecutar = getattr(modulo, "main", None)
        if not callable(ejecutar):
            raise TypeError(f"El módulo bots.{nombre} no tiene una función main")
        ejecutar()
    except SystemExit as error:
        if not capturar_errores:
            sys.exit(error.code)
        if error.code not in (None, 0):
            print(f"\n  ⚠️ {nombre} terminó con un error (código {error.code}).")
    except Exception as error:
        if not capturar_errores:
            raise
        print(f"\n  ❌ No se pudo completar la operación: {error}")
    finally:
        sys.argv = argv_original


def menu_estadisticas() -> None:
    """Muestra estadísticas actuales de la bóveda."""
    stats = obtener_estadisticas()
    print("\n" + _titulo("  📊 ESTADO DE LA BÓVEDA"))
    print(f"  Total de tweets registrados: {_estilizar(str(stats['total_tweets']), '1;37')}")
    print(f"  Borradores activos:          {_estilizar(str(stats['borradores']), '1;33')}")
    print()
    print(f"  ⌨️  Teclado   {stats['por_categoria']['teclado']:>4}")
    print(f"  🐙 GitHub    {stats['por_categoria']['github']:>4}")
    print(f"  📰 News      {stats['por_categoria']['news']:>4}")
    print(f"  💻 Código    {stats['por_categoria']['codigo']:>4}")
    print(f"  📦 Archivados {stats['por_categoria']['archivados']:>3}")
    print(_estilizar("\n  Los publicados se archivan automáticamente al revisar el estado.", "2"))


def menu_publicar() -> None:
    """Permite revisar, seleccionar y publicar un borrador en X."""
    borradores = listar_borradores()
    if not borradores:
        print("\n  ℹ️ No hay borradores disponibles para publicar.")
        return

    print("\n" + _titulo("  🚀 PUBLICAR BORRADOR EN X"))
    print(_estilizar("  Revisa el contenido antes de confirmar: la publicación es inmediata.", "2"))
    print()
    for i, borrador in enumerate(borradores, 1):
        titulo = borrador.get("titulo") or borrador.get("filename", "Sin título")
        categoria = borrador.get("category", "sin categoría")
        caracteres = len(borrador.get("tweet_text", ""))
        print(f"  {i:>2}. [{categoria:<7}] {titulo[:42]} ({caracteres} caracteres)")

    while True:
        opcion = input("\n  Número a publicar (c para cancelar): ").strip().lower()
        if opcion in ("c", "cancel", "q", "salir"):
            print("  ℹ️ Operación cancelada.")
            return
        if opcion.isdigit() and 1 <= int(opcion) <= len(borradores):
            break
        print(f"  ⚠️ Selecciona un número entre 1 y {len(borradores)}, o c para cancelar.")

    borrador = borradores[int(opcion) - 1]
    filepath = borrador["filepath"]
    texto = borrador.get("tweet_text", "")
    print(f"\n  {borrador.get('titulo', 'Sin título')}\n  {'─' * 60}\n{texto}\n  {'─' * 60}")
    if _confirmar("¿Confirmas la publicación en X?"):
        publicar_y_archivar_borrador(filepath)
    else:
        print("  ℹ️ Operación cancelada.")


def _accion_menu(eleccion: str) -> Callable[[], None] | None:
    """Construye la acción asociada a una opción del menú."""
    if eleccion == "1":
        return lambda: _ejecutar_bot("github_trending", [str(_leer_cantidad())])
    if eleccion == "2":
        return lambda: _accion_github_manual()
    if eleccion == "3":
        return lambda: _ejecutar_bot("news", [str(_leer_cantidad())])
    if eleccion == "4":
        return lambda: _ejecutar_bot("codigo", [str(_leer_cantidad())])
    if eleccion == "5":
        return lambda: _accion_retos()
    if eleccion == "6":
        return lambda: _ejecutar_bot("teclados", [str(_leer_cantidad())])
    if eleccion == "7":
        return lambda: _ejecutar_bot("mejorar_tweet", [])
    if eleccion == "8":
        return lambda: _ejecutar_bot("archivar", [])
    if eleccion == "9":
        return menu_publicar
    if eleccion == "10":
        return menu_estadisticas
    return None


def _accion_github_manual() -> None:
    """Solicita un repositorio y ejecuta el bot manual de GitHub."""
    repo = input("  Repositorio (ej. facebook/react, c para cancelar): ").strip()
    if repo.lower() in ("c", "cancel", "q"):
        print("  ℹ️ Operación cancelada.")
        return
    if repo:
        _ejecutar_bot("github_manual", [repo])
    else:
        print("  ⚠️ Debes indicar un repositorio.")


def _accion_retos() -> None:
    """Solicita los parámetros de un reto y ejecuta su bot."""
    lenguaje = input("  Lenguaje o tema (Enter para aleatorio): ").strip()
    dificultad = input("  Dificultad (facil, medio, dificil) [facil]: ").strip() or "facil"
    cantidad = _leer_cantidad()
    argumentos = [str(cantidad), dificultad] if not lenguaje else [lenguaje, str(cantidad), dificultad]
    _ejecutar_bot("retos", argumentos)


def menu_principal() -> None:
    """Ejecuta el menú interactivo hasta que el usuario decida salir."""
    while True:
        banner()
        mostrar_menu()
        try:
            eleccion = input("\n  Elige una opción (0-10): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  👋 ¡Hasta luego!")
            return

        if eleccion in OPCIONES_SALIDA:
            print("\n  👋 ¡Hasta luego!")
            return

        accion = _accion_menu(eleccion)
        if accion is None:
            print("\n  ⚠️ Opción no válida. Elige una opción del 0 al 10.")
            _pausar()
            continue

        try:
            accion()
        except (KeyboardInterrupt, EOFError):
            print("\n  ℹ️ Operación cancelada.")
        _pausar()


def _mostrar_ayuda() -> None:
    """Muestra los comandos disponibles para la ejecución directa."""
    print("Uso: python main.py [comando] [argumentos]")
    print("\nSin comando se abre el menú interactivo.")
    print("\nComandos: github, manual user/repo, news, codigo, retos, teclado,")
    print("          mejorar, archivar, stats")
    print("\nEjemplos:")
    print("  python main.py github 2")
    print("  python main.py manual facebook/react")
    print("  python main.py stats")


def main() -> None:
    """Punto de entrada CLI para el menú y los comandos individuales."""
    if len(sys.argv) == 1:
        menu_principal()
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]
    if cmd in ("-h", "--help", "help", "ayuda"):
        _mostrar_ayuda()
        return

    comandos = {
        "github": "github_trending",
        "github_trending": "github_trending",
        "trending": "github_trending",
        "manual": "github_manual",
        "gh": "github_manual",
        "news": "news",
        "hn": "news",
        "codigo": "codigo",
        "code": "codigo",
        "reto": "retos",
        "retos": "retos",
        "challenge": "retos",
        "challenges": "retos",
        "quiz": "retos",
        "teclado": "teclados",
        "teclados": "teclados",
        "reddit": "teclados",
        "mejorar": "mejorar_tweet",
        "improve": "mejorar_tweet",
        "archivar": "archivar",
        "archive": "archivar",
    }

    if cmd in comandos:
        if cmd in ("manual", "gh") and not args:
            print("Uso: python main.py manual user/repo")
            sys.exit(1)
        _ejecutar_bot(comandos[cmd], args, capturar_errores=False)
        return

    if cmd in ("stats", "estadisticas"):
        menu_estadisticas()
        return

    print(f"Comando desconocido: '{cmd}'")
    print("Comandos: github, manual, news, codigo, retos, teclado, mejorar, archivar, stats")
    sys.exit(1)


if __name__ == "__main__":
    main()
