"""Bot de Mejora de Tweets: lee borradores y los mejora con IA.

Uso: python -m bots.mejorar_tweet

Este bot interactivo:
1. Lista todos los tweets con status 'draft' en la bóveda de Obsidian
2. Permite seleccionar un tweet por ID
3. Usa IA para mejorarlo y hacerlo más viral
4. Agrega una sección 'Update' al archivo con el tweet mejorado
"""

import sys
from pathlib import Path
from typing import Optional

from src import config
from src.llm_client import generate_tweet
from src.obsidian_vault import (
    listar_tweets_boveda,
    obtener_tweet_por_id,
    agregar_update_tweet,
    _get_twitter_vault_path,
)

PROMPT_FILE = "prompts/prompt_mejorar_tweet.txt"


def mostrar_lista_tweets(tweets: list[dict], filtro: str = "todos") -> None:
    """Muestra la lista de tweets disponibles organizados por estado y ubicación."""
    print("\n" + "━" * 78)
    print(f"  📋 TWEETS EN LA BÓVEDA DE TWITTER (Filtro: {filtro.upper()})")
    print("━" * 78)

    if not tweets:
        print("  No se encontraron tweets con contenido para mostrar con este filtro.")
        print("━" * 78)
        return

    print(f"  {'#':<4} {'Estado':<12} {'Ubicación':<16} {'Título':<32} {'Chars':<8}")
    print("  " + "─" * 74)

    for i, t in enumerate(tweets, 1):
        status_label = "📝 draft" if t.get("status") == "draft" else "🚀 publicado"
        ubicacion = t.get("ubicacion", "twitter/")
        if len(ubicacion) > 15:
            ubicacion = ubicacion[:13] + ".."

        titulo = t.get("titulo") or t.get("title") or t.get("filename", "Sin título").replace(".md", "")
        if len(titulo) > 30:
            titulo = titulo[:27] + "..."

        chars = f"{t.get('char_count', len(t.get('tweet_text', '')))}c"

        print(f"  {i:<4} {status_label:<12} {ubicacion:<16} {titulo:<32} {chars:<8}")

    print("━" * 78)


def obtener_seleccion_usuario(todos_los_tweets: list[dict]) -> Optional[dict]:
    """Obtiene la selección del usuario con soporte de filtros rápidos y búsqueda."""
    tweets_visibles = list(todos_los_tweets)
    filtro_actual = "todos"

    while True:
        print("\n  💡 Opciones:")
        print("     • Escribe el número (#) o ID/título del tweet que deseas mejorar")
        print("     • Filtros: [b] borradores | [p] publicados | [t] todos")
        print("     • O 'q' para salir")
        print()

        try:
            seleccion = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  👋 ¡Hasta luego!")
            return None

        if not seleccion:
            continue

        sel_lower = seleccion.lower()

        if sel_lower in ("q", "quit", "exit", "salir"):
            print("\n  👋 ¡Hasta luego!")
            return None

        # Filtros rápidos
        if sel_lower in ("b", "borrador", "borradores", "draft", "drafts"):
            tweets_visibles = [t for t in todos_los_tweets if t.get("status") == "draft"]
            filtro_actual = "borradores"
            mostrar_lista_tweets(tweets_visibles, filtro=filtro_actual)
            continue
        elif sel_lower in ("p", "publicado", "publicados", "pub", "published"):
            tweets_visibles = [t for t in todos_los_tweets if t.get("status") == "published"]
            filtro_actual = "publicados"
            mostrar_lista_tweets(tweets_visibles, filtro=filtro_actual)
            continue
        elif sel_lower in ("t", "todo", "todos", "all"):
            tweets_visibles = list(todos_los_tweets)
            filtro_actual = "todos"
            mostrar_lista_tweets(tweets_visibles, filtro=filtro_actual)
            continue

        # Buscar por número de lista en la vista actual
        if seleccion.isdigit():
            idx = int(seleccion) - 1
            if 0 <= idx < len(tweets_visibles):
                elegido = tweets_visibles[idx]
                if not elegido.get("tweet_text", "").strip():
                    print(f"  ⚠️  El archivo '{elegido.get('filename')}' está vacío (sin texto de tweet para mejorar).")
                    continue
                return elegido
            else:
                print(f"  ⚠️  Número fuera de rango (1-{len(tweets_visibles)})")
                continue

        # Buscar por ID, filename o título en toda la bóveda
        tweet = obtener_tweet_por_id(seleccion, en_toda_la_boveda=True)
        if tweet:
            if not tweet.get("tweet_text", "").strip():
                print(f"  ⚠️  El archivo '{tweet.get('filename')}' no contiene texto de tweet para mejorar.")
                continue
            return tweet

        print(f"  ⚠️  No se encontró ningún tweet con: '{seleccion}'")
        print("     Intenta con el número (#), ID o parte del título mostrado en la lista.")


def mostrar_tweet_actual(tweet: dict) -> None:
    """Muestra el tweet actual antes de mejorarlo."""
    tweet_text = tweet.get("tweet_text", "No se pudo extraer el texto")
    titulo = tweet.get("titulo", tweet.get("filename", "Sin título"))
    rel_path = tweet.get("relative_path") or tweet.get("filename", "")
    status_label = "📝 Borrador" if tweet.get("status") == "draft" else "🚀 Publicado"

    print("\n" + "━" * 60)
    print("  📝 TWEET SELECCIONADO")
    print("━" * 60)
    print(f"  Título:     {titulo}")
    print(f"  Archivo:    {rel_path}")
    print(f"  Estado:     {status_label}")
    print(f"  Fuente:     {tweet.get('source', 'manual')}")
    print(f"  Caracteres: {len(tweet_text)}")
    if tweet.get("has_update"):
        print("  ℹ️  (Tiene sección 'Update' previa; se usará como base para mejorar)")
    print("─" * 60)
    print("\n  Texto actual:")
    print()
    for linea in tweet_text.split("\n"):
        print(f"    {linea}")
    print()
    print("━" * 60)


def detectar_si_es_hilo(tweet_text: str) -> tuple[bool, list[str]]:
    """Detecta si el texto es un hilo y lo separa en tweets individuales.
    
    Busca patrones comunes de hilos:
    - "1/12 Texto...", "2/12 Texto..." (número al inicio de cada tweet)
    - "1/12" en línea separada seguido del texto
    - "Tweet 1", "Tweet 2", etc.
    - "🧵" al inicio
    - Múltiples párrafos largos separados por líneas vacías
    - "---" explícitos
    """
    import re
    
    # Patrón 1: Números de hilo al inicio de cada tweet (1/12, 2/12, etc.)
    # Busca líneas que empiecen con N/M seguido de espacio y texto
    patron_numerico = re.compile(r'^\s*(\d+)\s*/\s*(\d+)\s+', re.MULTILINE)
    matches = patron_numerico.findall(tweet_text)
    
    if matches:
        total_tweets = int(matches[0][1])
        # Separar por el patrón N/M al inicio de línea
        # Usar lookahead para mantener el separador en el resultado
        tweets = re.split(r'(?=^\s*\d+\s*/\s*\d+\s+)', tweet_text, flags=re.MULTILINE)
        tweets = [t.strip() for t in tweets if t.strip()]
        
        if len(tweets) >= 2:
            return True, tweets
    
    # Patrón 2: "Tweet 1", "Tweet 2", etc. al inicio de cada tweet
    patron_tweet = re.compile(r'^\s*tweet\s+(\d+)\s*', re.MULTILINE | re.IGNORECASE)
    if patron_tweet.search(tweet_text):
        tweets = re.split(r'(?=^\s*tweet\s+\d+\s*)', tweet_text, flags=re.MULTILINE | re.IGNORECASE)
        tweets = [t.strip() for t in tweets if t.strip()]
        if len(tweets) >= 2:
            return True, tweets
    
    # Patrón 3: Hilo marcado con emoji 🧵
    if tweet_text.strip().startswith("🧵"):
        tweets = re.split(r'\n\n+', tweet_text)
        tweets = [t.strip() for t in tweets if t.strip()]
        if len(tweets) >= 2:
            return True, tweets
    
    # Patrón 4: Múltiples párrafos largos (cada uno podría ser un tweet)
    parrafos = re.split(r'\n\n+', tweet_text)
    parrafos = [p.strip() for p in parrafos if p.strip()]
    
    # Si hay 3+ párrafos y cada uno tiene más de 50 caracteres, probablemente es un hilo
    if len(parrafos) >= 3 and all(len(p) > 50 for p in parrafos):
        return True, parrafos
    
    # Patrón 5: Separadores explícitos ---
    if "\n---\n" in tweet_text:
        tweets = tweet_text.split("\n---\n")
        tweets = [t.strip() for t in tweets if t.strip()]
        if len(tweets) >= 2:
            return True, tweets
    
    return False, [tweet_text]


def mejorar_tweet_con_ia(tweet_text: str) -> Optional[str]:
    """Usa el LLM para mejorar el tweet."""
    print("\n  🤖 Mejorando tweet con IA...")
    
    # Detectar si es un hilo usando múltiples patrones
    es_hilo, tweets = detectar_si_es_hilo(tweet_text)
    
    print(f"  🔍 Detección: {'Hilo' if es_hilo else 'Tweet individual'} ({len(tweets)} elemento{'s' if len(tweets) > 1 else ''})")
    
    if es_hilo:
        tweets_mejorados = []
        
        print(f"\n  📝 Procesando {len(tweets)} tweets uno por uno...")
        print("  " + "─" * 50)
        
        for i, tweet in enumerate(tweets, 1):
            tweet_limpio = tweet.strip()
            chars = len(tweet_limpio)
            print(f"\n  [{i}/{len(tweets)}] Tweet original ({chars} chars):")
            print(f"  {tweet_limpio[:80]}..." if len(tweet_limpio) > 80 else f"  {tweet_limpio}")
            print(f"  Mejorando...", end=" ")
            
            try:
                mensaje = f"Tweet a mejorar ({chars} caracteres - mantén longitud similar):\n\n{tweet_limpio}"
                resultado = generate_tweet(
                    prompt_file=PROMPT_FILE,
                    user_message=mensaje,
                    max_reintentos=2,
                )
                
                # Verificar que no sea demasiado corto
                if len(resultado.strip()) < 20:
                    print(f"⚠️ Muy corto, reintentando...", end=" ")
                    resultado = generate_tweet(
                        prompt_file=PROMPT_FILE,
                        user_message=mensaje,
                        max_reintentos=1,
                    )
                
                tweets_mejorados.append(resultado.strip())
                print(f"✅ ({len(resultado.strip())} chars)")
            except Exception as e:
                print(f"❌ Error: {e}")
                tweets_mejorados.append(tweet_limpio)
        
        print("\n  " + "─" * 50)
        print(f"  ✅ Procesados {len(tweets_mejorados)}/{len(tweets)} tweets")
        
        return "\n---\n".join(tweets_mejorados)
    
    else:
        chars = len(tweet_text)
        print(f"  Tweet individual ({chars} caracteres)")
        print("  Mejorando...", end=" ")
        try:
            mensaje = f"Tweet a mejorar ({chars} caracteres - mantén longitud similar):\n\n{tweet_text}"
            resultado = generate_tweet(
                prompt_file=PROMPT_FILE,
                user_message=mensaje,
                max_reintentos=2,
            )
            print(f"✅ ({len(resultado.strip())} chars)")
            return resultado
        except Exception as e:
            print(f"\n  ❌ Error al mejorar el tweet: {e}")
            return None


def mostrar_comparacion(original: str, mejorado: str) -> None:
    """Muestra una comparación entre el original y el mejorado."""
    print("\n" + "━" * 60)
    print("  📊 COMPARACIÓN")
    print("━" * 60)

    # Detectar si es un hilo (contiene separadores ---)
    es_hilo = "\n---\n" in mejorado
    tweets_mejorados = mejorado.split("\n---\n") if es_hilo else [mejorado]
    tweets_originales = original.split("\n---\n") if "\n---\n" in original else [original]

    print(f"\n  📄 ORIGINAL ({len(tweets_originales)} tweets):")
    print("─" * 60)
    for tweet in tweets_originales:
        for linea in tweet.strip().split("\n"):
            print(f"    {linea}")
        print("    ---")

    print(f"\n  ✨ MEJORADO ({len(tweets_mejorados)} tweets):")
    print("─" * 60)
    for tweet in tweets_mejorados:
        for linea in tweet.strip().split("\n"):
            print(f"    {linea}")
        print("    ---")

    print("\n" + "━" * 60)
    if es_hilo:
        print(f"  Tweets: {len(tweets_originales)} → {len(tweets_mejorados)}")
    else:
        print(f"  Caracteres: {len(original)} → {len(mejorado)}")
    print("━" * 60)


def main() -> None:
    """Ejecución principal del bot de mejora de tweets."""
    print("\n" + "━" * 60)
    print("  🚀 BOT DE MEJORA DE TWEETS (BÓVEDA COMPLETA)")
    print("━" * 60)

    # Verificar configuración
    if not config.OBSIDIAN_VAULT_PATH and not getattr(config, "TWITTER_VAULT_PATH", None):
        print("\n  ❌ Error: OBSIDIAN_VAULT_PATH no configurado")
        print("  Configura esta variable en .env con la ruta a tu bóveda")
        sys.exit(1)

    if not config.LLM_API_KEY:
        print("\n  ❌ Error: LLM_API_KEY no configurado")
        print("  Configura tu API key del LLM en .env")
        sys.exit(1)

    vault_root = _get_twitter_vault_path()
    print(f"\n  📂 Explorando bóveda de Twitter: {vault_root}")
    tweets = listar_tweets_boveda(solo_con_texto=True, incluir_archivados=True)

    if not tweets:
        print("\n  ℹ️  No se encontraron tweets con contenido en la bóveda.")
        sys.exit(0)

    borradores_count = len([t for t in tweets if t.get("status") == "draft"])
    publicados_count = len([t for t in tweets if t.get("status") == "published"])
    print(f"  ✨ Total disponibles con contenido: {len(tweets)} ({borradores_count} borradores, {publicados_count} publicados)")

    # Mostrar lista y obtener selección
    mostrar_lista_tweets(tweets)
    tweet_seleccionado = obtener_seleccion_usuario(tweets)

    if not tweet_seleccionado:
        sys.exit(0)

    # Mostrar tweet actual
    mostrar_tweet_actual(tweet_seleccionado)

    # Confirmar mejora
    print("  ¿Deseas mejorar este tweet con IA? (s/n)")
    confirmacion = input("  > ").strip().lower()

    if confirmacion not in ("s", "si", "sí", "y", "yes"):
        print("\n  ℹ️  Operación cancelada.")
        sys.exit(0)

    # Mejorar tweet
    tweet_original = tweet_seleccionado.get("tweet_text", "")
    tweet_mejorado = mejorar_tweet_con_ia(tweet_original)

    if not tweet_mejorado:
        print("\n  ❌ No se pudo mejorar el tweet")
        sys.exit(1)

    # Mostrar comparación
    mostrar_comparacion(tweet_original, tweet_mejorado)

    # Confirmar guardado
    print("\n  ¿Deseas guardar esta mejora? (s/n)")
    print("  (Se agregará o actualizará la sección '## Update' en el archivo)")
    guardar = input("  > ").strip().lower()

    if guardar in ("s", "si", "sí", "y", "yes"):
        exito = agregar_update_tweet(
            filepath=tweet_seleccionado["filepath"],
            tweet_mejorado=tweet_mejorado,
        )

        if exito:
            rel_name = tweet_seleccionado.get("relative_path") or Path(tweet_seleccionado["filepath"]).name
            print("\n  ✅ ¡Tweet mejorado guardado exitosamente!")
            print(f"  📂 Archivo: {rel_name}")
            print("\n  Próximos pasos:")
            print("  1. Abre el archivo en Obsidian")
            print("  2. Revisa la sección 'Update'")
            print("  3. Copia el tweet mejorado cuando estés listo")
            print("  4. Publica en Twitter")
        else:
            print("\n  ❌ Error al guardar la mejora")
            sys.exit(1)
    else:
        print("\n  ℹ️  Mejora descartada.")

    print("\n" + "━" * 60)
    print("  👋 ¡Proceso completado!")
    print("━" * 60)


if __name__ == "__main__":
    main()
