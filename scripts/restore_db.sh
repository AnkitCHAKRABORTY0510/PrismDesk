#!/usr/bin/env bash
# Restore a Prism Desk backup created by backup_db.sh.
#
# Usage: scripts/restore_db.sh path/to/prism_desk_YYYYMMDD_HHMMSS.dump [target-database]
#
# Restoring REPLACES the objects in the target database. The safest
# procedure is to restore into a NEW empty database first, check it,
# then point backend/.env at it. See docs/DEPLOYMENT.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
FILE="${1:?Usage: restore_db.sh <backup.dump> [target-database]}"

read_env() {
  grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e 's/[[:space:]]*#.*$//'
}

DB_HOST="$(read_env DATABASE_HOST)"; DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="$(read_env DATABASE_PORT)"; DB_PORT="${DB_PORT:-5432}"
DB_USER="$(read_env DATABASE_USER)"; DB_USER="${DB_USER:-prism_user}"
TARGET="${2:-$(read_env DATABASE_NAME)}"
export PGPASSWORD="$(read_env DATABASE_PASSWORD)"

pg_restore --list "$FILE" > /dev/null

echo "About to restore $FILE into database '$TARGET' on $DB_HOST:$DB_PORT."
echo "Existing Prism Desk tables in '$TARGET' will be replaced."
read -r -p "Type the database name to continue: " CONFIRM
if [[ "$CONFIRM" != "$TARGET" ]]; then
  echo "Cancelled."
  exit 1
fi

pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TARGET" --clean --if-exists --no-owner "$FILE"
echo "Restore finished. Run 'alembic current' in backend/ to confirm the schema revision."
