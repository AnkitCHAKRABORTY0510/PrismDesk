# Moving Prism Desk to the lab workstation (IITG campus LAN)

A checklist for the move: copy the code, create a **new, empty** database, create the
real accounts and host Prism Desk for everyone on the campus network. Tick each box as you go.
The longer reference is [DEPLOYMENT.md](DEPLOYMENT.md); this file is the day-of plan.

Paths used below: code in `/opt/prism-desk`, a system user `prismdesk` runs the services,
Nginx serves the site.

**This workstation:** Ubuntu, hostname `prismdesk`, campus IP **`10.150.51.90`** (IITG Connect).
People on campus open **`https://10.150.51.90`**. The name `prismdesk` only works on other
machines if the IITG computer centre adds it to campus DNS (or a user adds
`10.150.51.90 prismdesk` to their own `/etc/hosts`); the configs accept both.

```
Campus browsers ──HTTPS──▶ Nginx :443 ──▶ /            frontend/dist (static files)
                                     └──▶ /api, /health → Uvicorn 127.0.0.1:8000 → PostgreSQL 127.0.0.1:5432
                            notification worker → PostgreSQL, Discord API (outbound, maybe via campus proxy)
```

---

## 0. Before you leave the laptop (today)

- [ ] **Commit the work** (recommended) so the workstation starts from a clean history. See
      "Uncommitted work" at the end; Claude asks before committing anything.
- [ ] Build the transfer package (secrets and junk are left out automatically):
  ```bash
  scripts/package_for_workstation.sh ~/prismdesk-transfer
  ```
  Options: `--bundle` also writes a git bundle (committed history only), `--with-data` adds
  the catalog caches in `backend/data/`, `--no-screenshots` drops the docs screenshots.
  It prints the package path, size and a `.sha256` checksum file next to it.
- [ ] Copy `prismdesk_<date>.tar.gz` and its `.sha256` to a USB drive (or scp them later).
- [ ] Write down on paper, **not** in a file you copy: the Discord bot token, client ID/secret,
      server (guild) ID and channel IDs from the laptop's `backend/.env`. Do not copy `.env` itself.
- [ ] **Regenerate the Discord bot token** in the Discord Developer Portal (Bot → Reset Token);
      the current one was shown in a debugging log on 2026-11-12. Use the new token on the
      workstation, and update the laptop's `backend/.env` too if you keep using it.
- [ ] Nothing from the laptop's database moves: the workstation gets a fresh database.

## 1. Prerequisites on the workstation

Versions used to build and test Prism Desk:

| Tool | Tested | Minimum |
|---|---|---|
| Ubuntu | 25.10 | 22.04+ |
| Python | 3.13.7 | 3.12 |
| Node.js / npm | 26.13 / 11.20 | Node 22 LTS (Vite 8 needs ≥ 20.19 / 22.12) |
| PostgreSQL | 17.10 | **15** (migrations use `NULLS NOT DISTINCT`) |
| Nginx | — | any current |

- [ ] If the campus network needs a proxy for internet access, set it for this shell first
      (ask the network admin for the address; add `user:password@` if it requires login):
  ```bash
  export http_proxy=http://<proxy-host>:<port> https_proxy=http://<proxy-host>:<port> no_proxy=localhost,127.0.0.1
  ```
  and for apt: `echo 'Acquire::http::Proxy "http://<proxy-host>:<port>";' | sudo tee /etc/apt/apt.conf.d/95proxy`
- [ ] Install system packages:
  ```bash
  sudo apt update && sudo apt install -y postgresql nginx python3-venv python3-pip curl
  ```
- [ ] Install Node.js 22 LTS or newer (only needed to build the frontend), e.g. from
      nodesource or `nvm`. Check: `node --version`.
- [ ] Set the hostname and check the campus IP:
  ```bash
  sudo hostnamectl set-hostname prismdesk && ip -4 addr | grep 10.150.51.90
  ```
  The IP must be the one IITG assigned (ask the computer centre to keep it fixed / reserved).
- [ ] Set the time zone (handbook dates use the server's local date):
  ```bash
  sudo timedatectl set-timezone Asia/Kolkata
  ```

## 2. Copy the code

- [ ] Check the archive and unpack it into `/opt`:
  ```bash
  sha256sum -c prismdesk_<date>.tar.gz.sha256
  ```
  ```bash
  sudo tar -xzf prismdesk_<date>.tar.gz -C /opt && ls /opt/prism-desk
  ```
  The archive unpacks into a `prism-desk/` folder, so this creates `/opt/prism-desk`.
  (Alternative with history: `git clone prismdesk_<date>.gitbundle /opt/prism-desk`. A bundle
  only holds **committed** work.)
- [ ] Create the service user and hand it the folder:
  ```bash
  sudo adduser --system --group --home /opt/prism-desk prismdesk && sudo chown -R prismdesk:prismdesk /opt/prism-desk
  ```
- [ ] `cat /opt/prism-desk/PACKAGE_INFO.txt` shows which commit/working state you copied.

## 3. New PostgreSQL database

- [ ] Keep PostgreSQL private to the machine: `listen_addresses = 'localhost'` in
      `/etc/postgresql/<version>/main/postgresql.conf` (the default), and never open port 5432.
- [ ] Create a database user with a **new** password (generate one with `openssl rand -base64 24`)
      and an empty database:
  ```bash
  sudo -u postgres createuser --pwprompt prism_user
  ```
  ```bash
  sudo -u postgres createdb --owner prism_user prism_desk
  ```

## 4. Backend configuration (`backend/.env`)

- [ ] Create it from the template and lock it down:
  ```bash
  cd /opt/prism-desk/backend && sudo -u prismdesk cp .env.example .env && sudo chmod 600 .env && sudo chown prismdesk:prismdesk .env
  ```
- [ ] Edit it (`sudo -u prismdesk nano .env`). Keep every comment on its own line: systemd does
      not strip `# ...` after a value. Set:

| Variable | Value |
|---|---|
| `APP_ENV` | `production` (HTTPS) — see §7 for an HTTP-only trial |
| `DATABASE_HOST` / `PORT` / `NAME` / `USER` | `127.0.0.1` / `5432` / `prism_desk` / `prism_user` (separate variables; there is no `DATABASE_URL`) |
| `DATABASE_PASSWORD` | the new password from §3 |
| `COOKIE_SECURE` | `true` with HTTPS |
| `CORS_ORIGINS` | `https://10.150.51.90,https://prismdesk` |
| `FRONTEND_BASE_URL` | `https://10.150.51.90` |
| `DISCORD_REDIRECT_URI` | `https://10.150.51.90/api/v1/notifications/discord/callback` |
| `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_BOT_TOKEN` (new), `DISCORD_GUILD_ID`, `DISCORD_ANNOUNCEMENT_CHANNEL_ID`, `DISCORD_RESEARCH_CHANNEL_ID`, `DISCORD_PROJECT_CATEGORY_ID` | from your notes |
| `OPENALEX_API_KEY` | optional, free from openalex.org |
| `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY` | only if the campus needs a proxy for outbound traffic (Discord DMs, DOI/arXiv/OpenAlex lookups, conference/journal catalogs). Keep `NO_PROXY=localhost,127.0.0.1,::1` |

  There is no app "secret key" to regenerate: sessions are random tokens stored hashed in the
  database. What must be new: the database password and the Discord bot token.

## 5. Install, migrate, first administrator

- [ ] Python environment:
  ```bash
  cd /opt/prism-desk/backend && sudo -u prismdesk python3 -m venv venv && sudo -u prismdesk venv/bin/pip install -r requirements.txt
  ```
- [ ] Create all tables in the new database (also seeds the four roles):
  ```bash
  cd /opt/prism-desk/backend && sudo -u prismdesk venv/bin/alembic upgrade head
  ```
  Expected last line: `Running upgrade a1b2c3d4e513 -> a1b2c3d4e514, task reminders…`.
  `sudo -u prismdesk venv/bin/alembic current` should print `a1b2c3d4e514 (head)`.
- [ ] Create **your** administrator account (interactive; it takes no arguments and only works
      while no administrator exists):
  ```bash
  cd /opt/prism-desk/backend && sudo -u prismdesk venv/bin/python -m scripts.create_admin
  ```
  It asks for Username, Email, Full name and a password of at least 12 characters (twice).
- [ ] Optional sanity run of the test suite. It uses a separate `prism_test` schema in the same
      database, never your data; drop it afterwards:
  ```bash
  cd /opt/prism-desk/backend && sudo -u prismdesk venv/bin/python -m pytest -q
  ```
  ```bash
  sudo -u postgres psql prism_desk -c 'DROP SCHEMA IF EXISTS prism_test CASCADE'
  ```

## 6. Frontend build

- [ ] Leave `VITE_API_BASE_URL` empty (same-origin through Nginx):
  ```bash
  cd /opt/prism-desk/frontend && sudo -u prismdesk cp .env.example .env
  ```
  ```bash
  cd /opt/prism-desk/frontend && sudo -u prismdesk npm ci && sudo -u prismdesk npm run build
  ```
  (With a proxy: `npm config set proxy http://<proxy>` and `npm config set https-proxy http://<proxy>` first.)
  The site is now in `frontend/dist/`.

## 7. Services, Nginx, HTTPS and the campus network

- [ ] Backend API and Discord notification worker as services (files already in the repo):
  ```bash
  sudo cp /opt/prism-desk/deploy/systemd/prism-desk-api.service /opt/prism-desk/deploy/systemd/prism-desk-notifications.service /etc/systemd/system/
  ```
  ```bash
  sudo systemctl daemon-reload && sudo systemctl enable --now prism-desk-api prism-desk-notifications
  ```
  Uvicorn listens on `127.0.0.1:8000` only; Nginx is the only thing reachable from the LAN.
- [ ] **HTTPS (recommended).** Get a certificate for `10.150.51.90`:
  - best: ask the IITG computer centre for a hostname and certificate; or
  - or a local certificate for the IP and hostname with mkcert:
    ```bash
    sudo apt install -y mkcert libnss3-tools && mkcert -install && mkcert 10.150.51.90 prismdesk
    ```
    ```bash
    sudo mkdir -p /etc/ssl/prism-desk && sudo mv 10.150.51.90+1.pem /etc/ssl/prism-desk/prism-desk.crt && sudo mv 10.150.51.90+1-key.pem /etc/ssl/prism-desk/prism-desk.key && sudo chmod 600 /etc/ssl/prism-desk/prism-desk.key
    ```
    Browsers on other machines show a warning until they trust mkcert's root CA
    (`mkcert -CAROOT` shows where `rootCA.pem` is; import it on lab PCs, never share `rootCA-key.pem`).
  `deploy/nginx/prism-desk.conf` already has `server_name 10.150.51.90 prismdesk;`. Install it:
  ```bash
  sudo cp /opt/prism-desk/deploy/nginx/prism-desk.conf /etc/nginx/sites-available/prism-desk && sudo ln -sf /etc/nginx/sites-available/prism-desk /etc/nginx/sites-enabled/prism-desk && sudo rm -f /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx
  ```
- [ ] **HTTP-only trial (if no certificate yet).** Use `deploy/nginx/prism-desk-http-only.conf`
      instead, and in `backend/.env` set `APP_ENV=development`, `COOKIE_SECURE=false` and
      `CORS_ORIGINS=http://10.150.51.90,http://prismdesk`, `FRONTEND_BASE_URL=http://10.150.51.90`,
      `DISCORD_REDIRECT_URI=http://10.150.51.90/api/v1/notifications/discord/callback`, then `sudo systemctl restart prism-desk-api`. With `APP_ENV=production`
      over plain HTTP nobody can log in (Secure cookies are forced). Session cookies are then
      unencrypted on the LAN, so move to HTTPS soon.
- [ ] Open the firewall for the web ports only:
  ```bash
  sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
  ```
  If the workstation's campus IP can change, ask the computer centre for a fixed IP/DNS name.
- [ ] `nginx` serves `/opt/prism-desk/frontend/dist`; make sure the `www-data` user can read it
      (`sudo chmod o+rx /opt/prism-desk /opt/prism-desk/frontend` and `o+r` on `dist/` if needed).

## 8. Discord

- [ ] Developer Portal → your application → OAuth2 → Redirects: add
      `https://10.150.51.90/api/v1/notifications/discord/callback` (the old localhost one can stay).
- [ ] Bot → Reset Token → put the new token in `backend/.env`, then
      `sudo systemctl restart prism-desk-api prism-desk-notifications`.
- [ ] The bot must already be in the lab Discord server (it needs a shared server to DM people;
      Manage Channels + Manage Roles for private project channels). See [discord-setup.md](discord-setup.md).
- [ ] Each user links Discord in Prism Desk under **Notifications**.

## 9. Real accounts

- [ ] You already created the administrator in §5.
- [ ] Everyone else opens `https://10.150.51.90/register` and signs up (username, email, full name,
      password). New accounts are **pending** and cannot log in yet.
- [ ] As administrator, approve them on the **Dashboard → Pending registrations** table (pick
      Student / Professor / Guest there) or under **User Management**. Give professors the
      Professor role so they can supervise projects, create official tasks and review.
- [ ] Professors (or you) create projects and add members; students can then be assigned tasks.
- [ ] Do not create real people's accounts with passwords you choose for them.

## 10. Catalog data (optional)

- [ ] Journal catalog (SCImago): scimagojr.com blocks automated downloads, so download the
      journal ranking CSV in a browser from scimagojr.com/journalrank.php ("Download data") and
      save it as `/opt/prism-desk/backend/data/scimagojr.csv` (owned by `prismdesk`). Without it the
      journal browser falls back to OpenAlex.
- [ ] The conference catalog downloads itself into `backend/data/` on first use (needs outbound
      internet, through the proxy if any). To skip the download you can package with `--with-data`.

## 11. Backups

- [ ] Daily backup at 02:30 as the `prismdesk` user:
  ```bash
  sudo -u prismdesk crontab -e
  ```
  add: `30 2 * * * /opt/prism-desk/scripts/backup_db.sh >> /opt/prism-desk/backups/backup.log 2>&1`
- [ ] Run it once by hand and check a `.dump` appears in `/opt/prism-desk/backups/`:
  ```bash
  sudo -u prismdesk /opt/prism-desk/scripts/backup_db.sh
  ```
- [ ] Copy `backups/` to another machine or drive regularly (a disk failure loses both).
      Restore steps: [DEPLOYMENT.md §9](DEPLOYMENT.md#9-restore).

## 12. Smoke test (from another computer on the LAN)

- [ ] `curl -k https://10.150.51.90/health` → ok, and `curl -k https://10.150.51.90/health/database` → ok.
- [ ] Open `https://10.150.51.90`, log in as the administrator, see the dashboard.
- [ ] Register a test student from another browser, approve it, log in as the student.
- [ ] Create a project, add the student, create an official task → the student gets a Discord DM
      (if Discord is linked). Student sends "Remind professor" → the professor gets a DM.
- [ ] Add a paper to the library (Quick add with a DOI) → metadata lookup works through the network.
- [ ] Toggle dark mode and open the site on a phone on campus Wi-Fi.
- [ ] Suspend the test student afterwards in User Management.

## 13. Troubleshooting

| Symptom | Check |
|---|---|
| Login form submits but you stay logged out | HTTP with `APP_ENV=production`/`COOKIE_SECURE=true` (see §7), or `CORS_ORIGINS`/`FRONTEND_BASE_URL` not matching the address in the browser bar exactly (scheme, host, no trailing slash). Restart the API after editing `.env`. |
| `502 Bad Gateway` | `sudo systemctl status prism-desk-api` and `journalctl -u prism-desk-api -n 100` |
| API won't start: database auth failed | password in `.env` (no inline comment after it!), `sudo -u postgres psql -c '\du'` |
| `relation ... does not exist` | migrations not applied: `venv/bin/alembic current` should show `a1b2c3d4e514 (head)` |
| No Discord DMs | worker log `journalctl -u prism-desk-notifications -f`; user linked Discord and kept the category on; bot shares a server with the user; proxy variables set in `.env` if the campus requires a proxy; new bot token in `.env` |
| Paper Quick add / journals / conferences time out | outbound internet blocked: set `HTTPS_PROXY`/`HTTP_PROXY` in `.env` and restart both services |
| Other machines can't open the site | `sudo ufw status`, `sudo ss -ltnp | grep nginx`, correct campus IP, same subnet/VLAN; some campus networks isolate Wi-Fi clients from wired machines |
| Dates in the handbook are a day off | time zone: `timedatectl` should show Asia/Kolkata |
| Blank page after an update | rebuild the frontend (`npm run build`) and hard-refresh the browser |

Updating later: copy the new code, then `venv/bin/pip install -r requirements.txt`,
`venv/bin/alembic upgrade head` (after `scripts/backup_db.sh`), `npm ci && npm run build`,
`sudo systemctl restart prism-desk-api prism-desk-notifications`.

## Uncommitted work (state on 2026-11-12)

The laptop repo's last commit is `dcf39da`; about 160 paths of finished work are uncommitted.
Grouped by feature (suggested one commit each):

1. **UI theme refresh**: theme tokens and dark mode (`index.css`, `ThemeContext`, UI primitives,
   layout, auth/admin/settings pages moved from fixed slate colours to tokens; removed `App.css`,
   `Login.css`, `Register.css`).
2. **Journals**: `models/journal.py`, `routes/journals.py`, `journal_service.py`,
   `journal_catalog.py` (SCImago/OpenAlex), migration `a1b2c3d4e509`, `pages/journals/`.
3. **Conference catalog**: `conference_catalog.py`, `ConferenceCatalog.tsx`, conference changes.
4. **Handbook planner and shared notes**: migrations `a1b2c3d4e510`, `a1b2c3d4e511`, planner/shared
   services and schemas, reminder dispatch, `pages/handbook/*`.
5. **Discord project channels and scheduled notifications**: migration `a1b2c3d4e512`,
   `discord_project_channels.py`, worker/notification service changes, `docs/discord-setup.md`.
6. **Paper metadata lookup**: `metadata_http.py`, `paper_metadata.py`, `doi_lookup.py`,
   `PaperFormModal.tsx`, research route/service changes.
7. **Dashboard redesign, reading status, GitHub links**: migration `a1b2c3d4e513`,
   `project_link*`, `pages/dashboard/*`, `ReadingStatusToggle`, `RepoLinksCard`, fonts.
8. **Task reminders**: migration `a1b2c3d4e514`, task model/service/routes, `ReminderFormModal`.
9. **Deployment**: this guide, `scripts/package_for_workstation.sh`, completed
   `backend/.env.example`, `deploy/nginx/prism-desk-http-only.conf`.

Nothing secret is in the working tree outside the gitignored `backend/.env` and `frontend/.env`.
