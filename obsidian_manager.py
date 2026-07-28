"""Gestor de tweets en Obsidian.

Permite ver el estado de los tweets y registrar publicaciones manuales.

Uso:
    python obsidian_manager.py estado          # Ver resumen
    python obsidian_manager.py borradores      # Listar borradores
    python obsidian_manager.py listos          # Listar tweets listos
    python obsidian_manager.py publicar ARCHIVO URL  # Registrar publicación
    python obsidian_manager.py analytics RUTA  # Subir CSV de analytics
"""

import sys
from pathlib import Path

from obsidian_vault import (
    obtener_estadisticas,
    listar_borradores,
    listar_listos,
    marcar_como_publicado,
    guardar_analytics,
)


def mostrar_estado() -> None:
    """Muestra el estado general de la bóveda."""
    stats = obtener_estadisticas()
    
    print("━" * 50)
    print("  📊 Estado de la Bóveda de Obsidian")
    print("━" * 50)
    print(f"\n  📝 Borradores: {stats['borradores']}")
    print(f"     - T2T (automáticos): {stats['borradores_t2t']}")
    print(f"     - Manuales: {stats['borradores_manual']}")
    print(f"\n  ✅ Listos para publicar: {stats['listos']}")
    print(f"\n  🐦 Publicados: {stats['publicados']}")
    print(f"\n  📈 Analytics: {stats['analytics_months']} meses de datos")
    print(f"\n{'━' * 50}")


def mostrar_borradores() -> None:
    """Muestra la lista de borradores pendientes."""
    borradores = listar_borradores()
    
    if not borradores:
        print("\n  No hay borradores pendientes.")
        return
    
    print("━" * 50)
    print("  📝 Borradores Pendientes")
    print("━" * 50)
    
    for i, b in enumerate(borradores, 1):
        print(f"\n  [{i}] {b.get('filename', 'Sin nombre')}")
        print(f"      Fuente: {b.get('source', 'N/A')}")
        print(f"      Fecha: {b.get('date', 'N/A')}")
        if b.get('repo'):
            print(f"      Repo: {b['repo']}")
        if b.get('stars'):
            print(f"      Stars: {b['stars']}")
        if b.get('tweet_text'):
            texto = b['tweet_text'][:100]
            print(f"      Tweet: {texto}...")
    
    print(f"\n{'━' * 50}")
    print(f"  Total: {len(borradores)} borradores")
    print(f"{'━' * 50}")


def mostrar_listos() -> None:
    """Muestra la lista de tweets listos para publicar."""
    listos = listar_listos()
    
    if not listos:
        print("\n  No hay tweets listos para publicar.")
        return
    
    print("━" * 50)
    print("  ✅ Listos para Publicar")
    print("━" * 50)
    
    for i, t in enumerate(listos, 1):
        print(f"\n  [{i}] {t.get('filename', 'Sin nombre')}")
        print(f"      Fuente: {t.get('source', 'N/A')}")
        if t.get('tweet_text'):
            print(f"      Tweet: {t['tweet_text']}")
        print(f"      Archivo: {t.get('filepath', 'N/A')}")
    
    print(f"\n{'━' * 50}")
    print(f"  Total: {len(listos)} tweets listos")
    print(f"\n  Para publicar:")
    print(f"  1. Copia el texto del tweet")
    print(f"  2. Pega en Twitter y publica")
    print(f"  3. Ejecuta: python obsidian_manager.py publicar ARCHIVO URL")
    print(f"{'━' * 50}")


def registrar_publicacion(archivo: str, url_tweet: str) -> None:
    """Registra una publicación manual.

    Args:
        archivo: Nombre del archivo del tweet.
        url_tweet: URL del tweet publicado.
    """
    # Buscar el archivo en listos
    listos = listar_listos()
    
    filepath = None
    for t in listos:
        if t.get("filename") == archivo or t.get("filepath") == archivo:
            filepath = t["filepath"]
            break
    
    if not filepath:
        # Intentar buscar por nombre parcial
        for t in listos:
            if archivo in t.get("filename", ""):
                filepath = t["filepath"]
                break
    
    if not filepath:
        print(f"  ❌ No se encontró el archivo: {archivo}")
        print(f"  Archivos disponibles:")
        for t in listos:
            print(f"    - {t.get('filename')}")
        return
    
    resultado = marcar_como_publicado(filepath, url_tweet)
    
    if resultado:
        print(f"  ✅ Tweet registrado como publicado")
        print(f"  📂 Archivo movido a: {Path(resultado).name}")
        print(f"  🔗 URL: {url_tweet}")
    else:
        print(f"  ❌ Error registrando la publicación")


def subir_analytics(ruta_csv: str) -> None:
    """Sube un CSV de analytics a la bóveda.

    Args:
        ruta_csv: Ruta al archivo CSV.
    """
    resultado = guardar_analytics(ruta_csv)
    
    if resultado:
        print(f"  ✅ Analytics guardado: {Path(resultado).name}")
    else:
        print(f"  ❌ Error guardando analytics")


def main() -> None:
    """Función principal."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    comando = sys.argv[1].lower()
    
    if comando == "estado":
        mostrar_estado()
    
    elif comando == "borradores":
        mostrar_borradores()
    
    elif comando == "listos":
        mostrar_listos()
    
    elif comando == "publicar":
        if len(sys.argv) < 4:
            print("Uso: python obsidian_manager.py publicar ARCHIVO URL_TWEET")
            print("Ejemplo: python obsidian_manager.py publicar 2026-07-28_free-llm.md https://x.com/usuario/status/123")
            sys.exit(1)
        registrar_publicacion(sys.argv[2], sys.argv[3])
    
    elif comando == "analytics":
        if len(sys.argv) < 3:
            print("Uso: python obsidian_manager.py analytics RUTA_CSV")
            print("Ejemplo: python obsidian_manager.py analytics ~/Downloads/analytics_2026-07.csv")
            sys.exit(1)
        subir_analytics(sys.argv[2])
    
    else:
        print(f"Comando desconocido: {comando}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
