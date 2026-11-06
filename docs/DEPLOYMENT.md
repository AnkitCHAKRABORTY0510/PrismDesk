# Prism Desk — Deployment Guide (Ubuntu lab workstation)

Target: one Ubuntu workstation running PostgreSQL, the FastAPI backend, the Discord notification
worker and Nginx. Lab users reach the app over the LAN through Nginx; PostgreSQL stays local.

```
LAN browsers ──HTTPS──▶ Nginx :443 ──▶ /            frontend/dist (static)
                                  └──▶ /api, /health Uvicorn 127.0.0.1:8000 ──▶ PostgreSQL 127.0.0.1:5432
                         notification worker ──▶ PostgreSQL, Discord API (outbound HTTPS)
```

Docker Compose is not used: the existing native setup (venv + system PostgreSQL) is kept.

## 1. Prerequisites
```bash
sudo apt install postgresql nginx python3-venv
```
Node.js 20+ is needed only to build the frontend.

## 2. PostgreSQL
1. Keep PostgreSQL bound to localhost: in `/etc/postgresql/<version>/main/postgresql.conf`
   `listen_addresses = 'localhost'`, and only `127.0.0.1/32`/`::1/128` entries in `pg_hba.conf`.
   Do not open port 5432 in the firewall.
2. Create the role and database (skip if they already exist):
```bash
sudo -u postgres createuser --pwprompt prism_user
```
```bash
sudo -u postgres createdb --owner prism_user prism_desk
```

## 3. Backend
```bash
cd /opt/prism-desk/backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt
```
```bash
cp .env.example .env && chmod 600 .env
```
Edit `.env` (see the comments in `.env.example`). Production values: `APP_ENV=production`,
`COOKIE_SECURE=true`, `SQL_ECHO=false`, `CORS_ORIGINS` and `FRONTEND_BASE_URL` set to the HTTPS
address users open.

Apply migrations and create the first administrator:
```bash
venv/bin/alembic upgrade head
```
```bash
venv/bin/python -m scripts.create_admin
```

### Environment variables
| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | development | `production` forces Secure cookies |
| `DATABASE_HOST/PORT/NAME/USER/PASSWORD` | 127.0.0.1/5432/prism_desk/prism_user/— | password required |
| `SQL_ECHO` | false | never enable on shared machines (logs parameters) |
| `LOG_LEVEL` | INFO | logs go to stdout → journald |
| `API_DOCS_ENABLED` | true | `/docs`, `/redoc`, `/openapi.json` |
| `SESSION_EXPIRE_HOURS` / `SESSION_INACTIVITY_MINUTES` | 8 / 30 | session lifetime |
| `SESSION_COOKIE_NAME` / `CSRF_HEADER_NAME` | prism_session / X-CSRF-Token | |
| `COOKIE_SECURE` | false | set true behind HTTPS |
| `CORS_ORIGINS` | localhost:5173 | comma-separated browser origins |
| `FRONTEND_BASE_URL` | http://localhost:5173 | used for the Discord OAuth redirect back to the UI |
| `RATE_LIMIT_ENABLED`, `LOGIN_RATE_LIMIT`, `REGISTER_RATE_LIMIT`, `RATE_LIMIT_WINDOW_SECONDS` | true, 10, 5, 300 | per client IP |
| `PROJECT_DELETE_RETENTION_DAYS` | 90 | recovery window |
| `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` | empty | OAuth2 account linking |
| `DISCORD_BOT_TOKEN`, `DISCORD_ANNOUNCEMENT_CHANNEL_ID` | empty | delivery |
| `NOTIFICATION_MAX_ATTEMPTS`, `NOTIFICATION_RETRY_BASE_SECONDS`, `NOTIFICATION_RETRY_MAX_SECONDS`, `NOTIFICATION_POLL_SECONDS` | 5, 60, 3600, 15 | backoff = base × 2^(attempt−1), capped |
| `TASK_REMINDER_HOURS`, `CONFERENCE_REMINDER_DAYS` | 24, 7 | reminder windows |

## 4. Discord setup (optional)
1. Create an application at the Discord Developer Portal. Under OAuth2 add the redirect
   `https://<host>/api/v1/notifications/discord/callback`; copy the client ID and secret to `.env`.
2. Add a Bot, copy its token to `DISCORD_BOT_TOKEN`, and invite it to the lab server (it needs to share
   a server with users to DM them, and "Send Messages" in the announcement channel).
3. Users link their account under **Notifications** in Prism Desk.
Without these values the app works normally; queued notifications are retried and then marked failed.

## 5. Frontend
```bash
cd /opt/prism-desk/frontend && npm ci && npm run build
```
Leave `VITE_API_BASE_URL` empty for the Nginx same-origin setup (see `frontend/.env.example`).

## 6. Services and Nginx
```bash
sudo cp deploy/systemd/prism-desk-api.service deploy/systemd/prism-desk-notifications.service /etc/systemd/system/
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now prism-desk-api prism-desk-notifications
```
```bash
sudo cp deploy/nginx/prism-desk.conf /etc/nginx/sites-available/prism-desk && sudo ln -s /etc/nginx/sites-available/prism-desk /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
```
Use a certificate trusted by lab machines (internal CA or `mkcert`); Secure cookies require HTTPS.
The API runs one Uvicorn worker so the in-process login rate limiter stays accurate.

Logs: `journalctl -u prism-desk-api -f` and `journalctl -u prism-desk-notifications -f`.
Health checks: `curl -k https://<host>/health` and `curl -k https://<host>/health/database`.

## 7. Local development
```bash
cd backend && venv/bin/uvicorn main:app --reload --port 8000
```
```bash
cd backend && venv/bin/python -m app.workers.notification_worker
```
```bash
cd frontend && npm run dev
```

## 8. Backups
```bash
scripts/backup_db.sh
```
Writes `backups/prism_desk_<timestamp>.dump` (pg_dump custom format, mode 600), verifies it with
`pg_restore --list`, and keeps the newest 30. Schedule it daily, for example with `crontab -e`:
```
30 2 * * * /opt/prism-desk/scripts/backup_db.sh >> /var/log/prism-desk-backup.log 2>&1
```
**Limitation:** backups on the same workstation are lost with the disk. Copy `backups/` to an external
drive or another machine (for example `rsync -a backups/ backup-host:/srv/prism-desk-backups/`).

## 9. Restore
Safest path — restore into a new database, verify, then switch:
```bash
sudo -u postgres createdb --owner prism_user prism_desk_restore
```
```bash
scripts/restore_db.sh backups/prism_desk_YYYYMMDD_HHMMSS.dump prism_desk_restore
```
Check the data, then set `DATABASE_NAME=prism_desk_restore` in `backend/.env` and restart both
services. `restore_db.sh` asks you to type the target database name before it replaces anything.

## 10. Maintenance
- Permanently delete projects older than the 90-day window from **Projects → Deleted** (administrator).
- Audit logs are append-only; define a retention policy before production (Phase 0 decision D-11).
- Expired session rows accumulate harmlessly; they can be pruned with
  `DELETE FROM user_sessions WHERE expires_at < now() - interval '30 days';` during maintenance.
