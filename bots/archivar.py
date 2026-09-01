"""Bot de Archivo: detecta tweets marcados como 'published' en Obsidian y los mueve a 'archivados/'.

Uso:
    python -m bots.archivar
"""

from src.obsidian_vault import archivar_publicados, obtener_estadisticas


def main() -> None:
    """Ejecuta el escaneo y archivo de notas publicadas."""
    print("━" * 50)
    print("  📦 Archivador de Tweets Publicados")
    print("━" * 50)

    movidos = archivar_publicados()
    if movidos:
        print(f"\n✅ Se archivaron {len(movidos)} tweet(s) publicado(s).")
    else:
        print("\nℹ️  No hay tweets nuevos pendientes de archivar.")

    stats = obtener_estadisticas()
    print("\n📊 Estado de la bóveda:")
    print(f"  • Borradores activos: {stats['borradores']}")
    print(f"    - Teclado: {stats['por_categoria']['teclado']}")
    print(f"    - GitHub:  {stats['por_categoria']['github']}")
    print(f"    - News:    {stats['por_categoria']['news']}")
    print(f"    - Código:  {stats['por_categoria']['codigo']}")
    print(f"  • Total archivados / publicados: {stats['por_categoria']['archivados']}")
    print("━" * 50)


if __name__ == "__main__":
    main()
