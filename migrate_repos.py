"""Script para marcar repos ya publicados como procesados.

Ejecutar una sola vez en Railway para evitar repetir repos.
"""

import os
# Establecer ruta de DB antes de importar metrics_db
os.environ.setdefault("METRICS_DB_PATH", "/data/metrics.db")

from metrics_db import init_db, registrar_tweet, is_processed

# Repos que ya fueron publicados en Twitter
REPOS_YA_PUBLICADOS = [
    {"tweet_id": "gh_676676006", "texto": "Fooocus", "source": "github", "item_id": "gh_676676006"},
    {"tweet_id": "gh_1183888342", "texto": "Orca", "source": "github", "item_id": "gh_1183888342"},
    {"tweet_id": "gh_1096736638", "texto": "grok-build", "source": "github", "item_id": "gh_1096736638"},
]


def main():
    """Marca los repos como procesados."""
    init_db()
    
    print("Marcando repos ya publicados como procesados...")
    print("━" * 50)
    
    for repo in REPOS_YA_PUBLICADOS:
        if is_processed(repo["item_id"]):
            print(f"  ⏭  Ya existe: {repo['item_id']} ({repo['texto']})")
            continue
        
        try:
            registrar_tweet(
                tweet_id=repo["tweet_id"],
                texto=repo["texto"],
                source=repo["source"],
                item_id=repo["item_id"],
            )
            print(f"  ✅ Registrado: {repo['item_id']} ({repo['texto']})")
        except Exception as e:
            print(f"  ❌ Error: {repo['item_id']} - {e}")
    
    print("━" * 50)
    print("Completado.")


if __name__ == "__main__":
    main()
