#!/bin/bash
# Importa la DB de Railway a local
# Uso: ./import_db.sh

set -e

DB_PATH="metrics.db"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📥 Importando DB desde Railway..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Exportar DB desde Railway
railway run python export_db.py > /tmp/railway_dump.sql 2>/dev/null

# Verificar si hay datos
if grep -q "EMPTY" /tmp/railway_dump.sql || [ ! -s /tmp/railway_dump.sql ]; then
    echo "  ⚠️  No hay datos en Railway aún"
    rm -f /tmp/railway_dump.sql
    exit 0
fi

# Crear DB local desde el dump
echo "  💾 Creando DB local..."
rm -f "$DB_PATH"
sqlite3 "$DB_PATH" < /tmp/railway_dump.sql

# Contar tweets
COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM tweets;")
echo "  ✅ Sincronizados $COUNT tweets"

rm -f /tmp/railway_dump.sql
