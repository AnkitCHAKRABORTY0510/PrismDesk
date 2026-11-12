#!/usr/bin/env bash
# Build a clean transfer package of Prism Desk for the lab workstation.
#
# Usage: scripts/package_for_workstation.sh [output-dir] [--with-data] [--no-screenshots] [--bundle]
#
#   output-dir        where to write the package (default: ~/prismdesk-transfer, outside the repo)
#   --with-data       also include backend/data/ (conference/journal catalog caches; no secrets)
#   --no-screenshots  leave out docs/*-redesign/ screenshot folders (~20 MB)
#   --bundle          also write a git bundle of the committed history (uncommitted work is NOT in it)
#
# What goes in: every file git tracks plus new files that are not gitignored
# (`git ls-files -co --exclude-standard`), i.e. the working tree as it is now,
# including uncommitted work. What stays out, because .gitignore excludes it:
# backend/.env, frontend/.env, backend/venv, frontend/node_modules, dist,
# backups/, backend/data/ (unless --with-data), __pycache__, test caches.
# The stray shadcn folder frontend/@ (not imported anywhere) is also left out.
#
# Before finishing, the script checks the package for the secret values in
# backend/.env (database password, Discord secrets/token) and refuses to
# keep it if any is found. Nothing in the repository is modified.
set -euo pipefail
set +x  # never trace: the secret scan handles real secret values

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$HOME/prismdesk-transfer"
WITH_DATA=0
SCREENSHOTS=1
BUNDLE=0
for arg in "$@"; do
  case "$arg" in
    --with-data) WITH_DATA=1 ;;
    --no-screenshots) SCREENSHOTS=0 ;;
    --bundle) BUNDLE=1 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    -*) echo "Unknown option $arg" >&2; exit 2 ;;
    *) OUT_DIR="$arg" ;;
  esac
done

case "$(cd "$(dirname "$OUT_DIR")" 2>/dev/null && pwd)/$(basename "$OUT_DIR")/" in
  "$ROOT"/*) echo "Choose an output directory outside the repository." >&2; exit 2 ;;
esac

STAMP="$(date +%Y%m%d_%H%M%S)"
NAME="prismdesk_${STAMP}"
mkdir -p "$OUT_DIR"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cd "$ROOT"
git ls-files -co --exclude-standard -z \
  | tr '\0' '\n' \
  | grep -vE '^frontend/@/' \
  | { if [[ $SCREENSHOTS -eq 0 ]]; then grep -vE '^docs/[^/]+-redesign/'; else cat; fi; } \
  | while IFS= read -r f; do [[ -f "$f" ]] && printf '%s\n' "$f"; done \
  > "$WORK/files.txt"
if [[ $WITH_DATA -eq 1 && -d backend/data ]]; then
  find backend/data -type f >> "$WORK/files.txt"
fi

# Belt and braces: never ship env files, dumps or keys even if .gitignore changes.
if grep -E '(^|/)\.env$|\.dump$|\.pem$|\.key$|(^|/)venv/|node_modules/' "$WORK/files.txt"; then
  echo "Refusing: the file list above must not be packaged." >&2
  exit 1
fi

# Record exactly which source state this is.
{
  echo "Prism Desk transfer package $NAME"
  echo "Created: $(date -Iseconds) on $(hostname)"
  echo "Git commit: $(git rev-parse --short HEAD) ($(git log -1 --format=%s))"
  echo "Uncommitted changes included: $(git status --porcelain | wc -l) paths"
  echo "Alembic head: $(grep -l "^revision = " backend/alembic/versions/*.py | xargs grep -h '^revision = ' | wc -l) revisions"
  echo
  echo "Not included (recreate on the workstation): backend/.env, frontend/.env, backend/venv,"
  echo "frontend/node_modules, frontend/dist, backups/, database contents."
  echo "Follow docs/DEPLOY_WORKSTATION.md."
} > "$WORK/PACKAGE_INFO.txt"

tar -czf "$OUT_DIR/$NAME.tar.gz" \
  --transform "s,^,prism-desk/," \
  -T "$WORK/files.txt" \
  -C "$WORK" PACKAGE_INFO.txt

# Secret scan: look for the real secret values from backend/.env inside the package.
if [[ -f backend/.env ]]; then
  mkdir "$WORK/extract"
  tar -xzf "$OUT_DIR/$NAME.tar.gz" -C "$WORK/extract"
  leaked=0
  for key in DATABASE_PASSWORD DISCORD_CLIENT_SECRET DISCORD_BOT_TOKEN OPENALEX_API_KEY; do
    value="$( (grep -E "^$key=" backend/.env || true) | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e 's/[[:space:]]*#.*$//')"
    # Never echo the value itself.
    if [[ ${#value} -ge 6 ]]; then
      if grep -rqF -- "$value" "$WORK/extract"; then
        echo "Secret value of $key found inside the package." >&2
        leaked=1
      fi
    fi
  done
  if [[ $leaked -eq 1 ]]; then
    rm -f "$OUT_DIR/$NAME.tar.gz"
    echo "Package deleted. Remove the secret from the file(s) above and retry." >&2
    exit 1
  fi
fi

(cd "$OUT_DIR" && sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256")

if [[ $BUNDLE -eq 1 ]]; then
  git bundle create "$OUT_DIR/$NAME.gitbundle" --all
  git bundle verify "$OUT_DIR/$NAME.gitbundle" >/dev/null
  echo "Git bundle (committed history only): $OUT_DIR/$NAME.gitbundle"
fi

echo "Package:  $OUT_DIR/$NAME.tar.gz ($(du -h "$OUT_DIR/$NAME.tar.gz" | cut -f1), $(wc -l < "$WORK/files.txt") files)"
echo "Checksum: $OUT_DIR/$NAME.tar.gz.sha256"
echo "Secret scan: passed (no backend/.env secret values inside)."
