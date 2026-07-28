#!/usr/bin/env python3
"""Sincroniza la bóveda de Obsidian con el repositorio Git.

Este script:
1. Hace pull de los últimos cambios
2. Ejecuta la operación principal (scheduler, bot, etc.)
3. Hace push de los cambios al terminar

Uso:
    python sync_obsidian.py [comando]

Ejemplo:
    python sync_obsidian.py python scheduler.py
"""

import os
import subprocess
import sys
from pathlib import Path


OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")
OBSIDIAN_REPO_URL = os.getenv("OBSIDIAN_REPO_URL", "")


def sync_pull() -> bool:
    """Hace pull de los últimos cambios de la bóveda."""
    if not OBSIDIAN_VAULT_PATH or not OBSIDIAN_REPO_URL:
        print("⚠️  OBSIDIAN_VAULT_PATH u OBSIDIAN_REPO_URL no configurados")
        return False
    
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    
    # Si el directorio no existe, clonar el repo
    if not vault_path.exists():
        print(f"📥 Clonando bóveda de Obsidian...")
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", OBSIDIAN_REPO_URL, str(vault_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Error clonando: {result.stderr}")
            return False
        print("✅ Bóveda clonada")
        return True
    
    # Si ya existe, hacer pull
    print("📥 Actualizando bóveda de Obsidian...")
    result = subprocess.run(
        ["git", "pull", "--rebase"],
        cwd=str(vault_path),
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"⚠️  Pull falló (puede ser primer push): {result.stderr}")
        # No es error fatal, continuar
    
    print("✅ Bóveda actualizada")
    return True


def sync_push(mensaje: str = "update: sincronizar bóveda") -> bool:
    """Hace push de los cambios a la bóveda."""
    if not OBSIDIAN_VAULT_PATH:
        return False
    
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    
    if not vault_path.exists():
        return False
    
    print("📤 Subiendo cambios a la bóveda...")
    
    # Agregar todos los cambios
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(vault_path),
        capture_output=True,
    )
    
    # Verificar si hay cambios
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(vault_path),
        capture_output=True,
        text=True,
    )
    
    if not result.stdout.strip():
        print("✅ No hay cambios para subir")
        return True
    
    # Commit
    subprocess.run(
        ["git", "commit", "-m", mensaje],
        cwd=str(vault_path),
        capture_output=True,
    )
    
    # Push
    result = subprocess.run(
        ["git", "push"],
        cwd=str(vault_path),
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"❌ Error subiendo: {result.stderr}")
        return False
    
    print("✅ Cambios subidos")
    return True


def main():
    """Punto de entrada principal."""
    if len(sys.argv) < 2:
        print("Uso: python sync_obsidian.py [comando]")
        print("Ejemplo: python sync_obsidian.py python scheduler.py")
        sys.exit(1)
    
    # 1. Pull antes de ejecutar
    sync_pull()
    
    # 2. Ejecutar el comando
    print(f"\n{'━' * 50}")
    print(f"  Ejecutando: {' '.join(sys.argv[1:])}")
    print(f"{'━' * 50}\n")
    
    result = subprocess.run(sys.argv[1:])
    
    # 3. Push después de ejecutar
    print(f"\n{'━' * 50}")
    print(f"  Sincronizando bóveda...")
    print(f"{'━' * 50}")
    
    sync_push(f"update: después de ejecutar {' '.join(sys.argv[1:])}")
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
