#!/usr/bin/env bash
# Back up the Prism Desk database with pg_dump (custom format).
#
# Usage: scripts/backup_db.sh [backup-directory]
# Reads connection settings from backend/.env. The password is passed
# through PGPASSWORD and never printed. Keeps the newest 30 backups.
#
# Backups stored on the same workstation do not survive disk failure or
# theft. Copy them to an external drive or another machine regularly,
# for example:  rsync -a backups/ backup-host:/srv/prism-desk-backups/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
DEST="${1:-$ROOT/backups}"
KEEP="${PRISM_BACKUP_KEEP:-30}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

read_env() {
  grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e 's/[[:space:]]*#.*$//'
}

DB_HOST="$(read_env DATABASE_HOST)"; DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="$(read_env DATABASE_PORT)"; DB_PORT="${DB_PORT:-5432}"
DB_NAME="$(read_env DATABASE_NAME)"; DB_NAME="${DB_NAME:-prism_desk}"
DB_USER="$(read_env DATABASE_USER)"; DB_USER="${DB_USER:-prism_user}"
export PGPASSWORD="$(read_env DATABASE_PASSWORD)"

mkdir -p "$DEST"
chmod 700 "$DEST"
FILE="$DEST/prism_desk_$(date +%Y%m%d_%H%M%S).dump"

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -Fc -f "$FILE"
chmod 600 "$FILE"
pg_restore --list "$FILE" > /dev/null   # verify the archive is readable

echo "Backup written: $FILE ($(du -h "$FILE" | cut -f1))"

# Retention: delete only older Prism Desk backup files in this folder.
ls -1t "$DEST"/prism_desk_*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f --
