"""Script para marcar repos ya publicados como procesados.

Ejecutar una sola vez para evitar repetir repos.
"""

import os
import sys
from pathlib import Path

# Intentar usar la ruta de Railway, si no existe usar local
DB_PATH = os.getenv("METRICS_DB_PATH", "/data/metrics.db")
if not Path(DB_PATH).parent.exists():
    DB_PATH = "metrics.db"
    print(f"  ℹ️  Usando DB local: {DB_PATH}")
else:
    print(f"  ℹ️  Usando DB de Railway: {DB_PATH}")

os.environ["METRICS_DB_PATH"] = DB_PATH

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
