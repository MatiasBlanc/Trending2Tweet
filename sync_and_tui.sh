#!/bin/bash
# Descarga la DB de Railway y abre la TUI
# Uso: ./sync_and_tui.sh

set -e

DB_PATH="metrics.db"
REMOTE_SCRIPT="from metrics_db import init_db, _get_connection; init_db(); conn = _get_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM tweets'); print(f'Tweets: {cursor.fetchone()[0]}'); conn.close()"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔄 Sincronizando DB desde Railway..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Crear script temporal para exportar la DB
EXPORT_SCRIPT=$(cat << 'EOF'
import sqlite3
import sys
from pathlib import Path

# Conectar a la DB del volumen
db_path = "/data/metrics.db"
if not Path(db_path).exists():
    print("ERROR: No existe la DB en /data/metrics.db")
    sys.exit(1)

# Leer y exportar como SQL
conn = sqlite3.connect(db_path)
dump = "\n".join(conn.iterdump())
conn.close()

# Escribir a stdout
print(dump)
EOF
)

# Ejecutar en Railway y guardar como SQL temporal
echo "  📥 Exportando datos desde Railway..."
railway run python -c "
import sqlite3, sys
from pathlib import Path

db_path = '/data/metrics.db'
if not Path(db_path).exists():
    print('EMPTY')
    sys.exit(0)

conn = sqlite3.connect(db_path)
for line in conn.iterdump():
    print(line)
conn.close()
" > /tmp/railway_dump.sql 2>/dev/null

# Verificar si hay datos
if grep -q "EMPTY" /tmp/railway_dump.sql || [ ! -s /tmp/railway_dump.sql ]; then
    echo "  ⚠️  No hay datos en Railway aún"
    echo ""
else
    # Crear DB local desde el dump
    echo "  💾 Creando DB local..."
    rm -f "$DB_PATH"
    sqlite3 "$DB_PATH" < /tmp/railway_dump.sql
    
    # Contar tweets
    COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM tweets;")
    echo "  ✅ Sincronizados $COUNT tweets"
fi

rm -f /tmp/railway_dump.sql

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Abriendo TUI..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Abrir TUI
./tui
