# Connecting Prism Desk to Discord

Prism Desk sends all of its notifications through Discord. This guide takes you from nothing to a
working setup: a Discord application, a bot in your lab server, the `.env` values, the background
worker, and a test message to your own account.

You need about 15 minutes, a Discord account, and **Manage Server** permission on the lab's Discord
server (you need it to add the bot).

## How it works

| What | How Prism Desk sends it | Needs |
|---|---|---|
| Personal notifications (tasks, projects, conference deadlines, handbook comments, **planner reminders**, account approval) | **Direct message** from the bot to each person who linked their account | Their linked account, the category switched on in Notification Settings, and **the bot and that person in at least one shared server** |
| Admin announcements (Admin → Announcements) | A post in the announcement channel, and optionally a DM to every linked user | `DISCORD_ANNOUNCEMENT_CHANNEL_ID` |
| Paper added **to a project** | A post (with a discussion thread) in that **project's private channel**; only project members can see it. If the channel does not exist yet, a DM to each other team member instead | `DISCORD_GUILD_ID`, bot permissions Manage Channels + Manage Roles |
| **General** paper or video link (no project) | A post in the research channel with a discussion thread, **and** a DM to every linked lab member (guests excluded) | `DISCORD_RESEARCH_CHANNEL_ID` for the post (and `DISCORD_GUILD_ID` for "Discuss on Discord" links); DMs need only linked accounts |

The website itself never talks to Discord when you click something. It writes a row to an
**outbox** table, and a separate **notification worker** process sends the rows. So nothing is
delivered unless the worker is running (step 9).

Account linking uses Discord's OAuth2 login with the `identify` scope only: Prism Desk learns the
user's Discord ID and name and nothing else, and never stores their Discord password or tokens.

---

## 1. Create the Discord application

1. Open <https://discord.com/developers/applications> and sign in.
2. Click **New Application** (top right), name it (for example `Prism Desk`), accept the terms,
   and click **Create**.
3. On the **General Information** page, copy the **Application ID**. This is your
   `DISCORD_CLIENT_ID`.

## 2. OAuth2: client secret and redirect URI

1. In the left menu click **OAuth2**.
2. Under **Client Secret**, click **Reset Secret**, confirm, and copy the value. This is your
   `DISCORD_CLIENT_SECRET`. Discord shows it only once; if you lose it, reset it again.
3. Under **Redirects**, click **Add Redirect** and paste the callback URL of your backend,
   then click **Save Changes**:

   | Where Prism Desk runs | Redirect URI |
   |---|---|
   | Your own computer (uvicorn on port 8000, Vite on 5173) | `http://localhost:8000/api/v1/notifications/discord/callback` |
   | The lab server behind Nginx | `https://<your-host>/api/v1/notifications/discord/callback` |

   The value must match `DISCORD_REDIRECT_URI` in `.env` **character for character** (scheme,
   host, port, path, no trailing slash).

> **Local development:** open the app at `http://localhost:5173`, not `http://127.0.0.1:5173`.
> The callback reads your Prism Desk login cookie, and browsers treat `localhost` and `127.0.0.1`
> as different sites, so mixing them makes the link fail with "Discord linking failed".

## 3. Bot: get the token

1. In the left menu click **Bot**.
2. Click **Reset Token**, confirm, and copy it. This is your `DISCORD_BOT_TOKEN`.
   Treat it like a password: anyone holding it controls the bot. Never commit it or paste it into
   chat; if it leaks, click **Reset Token** again.
3. On the same page:
   - **Public Bot**: you can turn this **off** so only you can add the bot to servers.
   - **Requires OAuth2 Code Grant**: leave **off**.
   - **Privileged Gateway Intents** (Presence, Server Members, Message Content): leave all **off**.
     Prism Desk only calls Discord's REST API and never reads messages, so it needs no intents.
4. Click **Save Changes** if you changed anything.

## 4. Invite the bot to your lab server

Prism Desk needs these bot permissions:

| Permission | Why |
|---|---|
| View Channels | see the announcement and research channels |
| Send Messages | post announcements and papers |
| Read Message History | start a thread on its own paper post |
| Create Public Threads | the discussion thread for each new paper |
| Send Messages in Threads | post into those threads |
| Manage Channels | create and rename one private channel per project |
| Manage Roles | let only a project's members see its channel (channel permission overwrites) |
| Embed Links, Attach Files, Add Reactions | the bot can only give project members permissions it has itself |

Together that is the permission integer **`309506198608`**. Open this URL in your browser, with
your Application ID in place of `YOUR_CLIENT_ID`:

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=309506198608
```

Pick the lab server, click **Continue**, then **Authorize**. The bot appears in the member list
(offline — that is normal, it never connects to the live gateway).

(You can also build this URL in the portal under **OAuth2 → URL Generator**: tick `bot`, then tick
the permissions above.)

**Already invited the bot with fewer permissions?** Open the link above again and authorize: Discord
updates the bot's role. Or in Discord: Server Settings → Roles → the bot's role (named after the
bot) → Permissions → switch on **Manage Channels**, **Manage Roles**, **Embed Links**, **Attach Files** and
**Add Reactions**.

**Direct messages need a shared server.** Discord lets a bot DM someone only if they are both in
at least one server, and only if that person allows DMs from members of that server (Discord user
settings → *Privacy & Safety* → *Allow direct messages from server members*, or the per-server
*Privacy Settings*). Everyone who wants notifications must be in the lab server.

If a channel is private, also add the bot (or a role it has) to that channel's permissions.

## 5. Copy the server and channel IDs

1. In the Discord app open **User Settings → Advanced** and switch on **Developer Mode**.
2. Right-click the lab server icon → **Copy Server ID**. This is `DISCORD_GUILD_ID`.
3. Right-click the channel for announcements → **Copy Channel ID**. This is
   `DISCORD_ANNOUNCEMENT_CHANNEL_ID`.
4. Right-click the channel for new papers → **Copy Channel ID**. This is
   `DISCORD_RESEARCH_CHANNEL_ID`. It must be a normal text channel (threads are created on its posts).

All three are optional: leave one empty and that feature is simply skipped.

## 6. Fill in `backend/.env`

Add these lines to `backend/.env` (the file is not in git; never commit it). Replace the
placeholder values with yours:

```dotenv
# Where the browser opens the app; the OAuth callback redirects back here.
FRONTEND_BASE_URL=http://localhost:5173

DISCORD_CLIENT_ID=123456789012345678
DISCORD_CLIENT_SECRET=paste-client-secret-here
DISCORD_REDIRECT_URI=http://localhost:8000/api/v1/notifications/discord/callback
DISCORD_BOT_TOKEN=paste-bot-token-here
DISCORD_ANNOUNCEMENT_CHANNEL_ID=111111111111111111
DISCORD_RESEARCH_CHANNEL_ID=222222222222222222
DISCORD_GUILD_ID=333333333333333333
```

On the lab server use `https://<your-host>` for `FRONTEND_BASE_URL` and the HTTPS redirect URI.

Optional tuning (defaults shown):

```dotenv
NOTIFICATION_POLL_SECONDS=15        # how often the worker checks the outbox
NOTIFICATION_MAX_ATTEMPTS=5         # retries for temporary Discord errors
TASK_REMINDER_HOURS=24              # "task due soon" lead time
CONFERENCE_REMINDER_DAYS=7          # "conference deadline" lead time
```

## 7. Restart the backend

Settings are read once at start-up.

- Local: stop uvicorn (Ctrl+C) and start it again, e.g. `venv/bin/uvicorn main:app --reload`
  from `backend/` (`--reload` does **not** pick up `.env` changes).
- Lab server: `sudo systemctl restart prism-desk-api`

## 8. Check the configuration

Log in to Prism Desk and open **Notifications** (sidebar, Account section) (`/settings/notifications`). With the
OAuth values set you see a **Link with Discord** button instead of "Discord linking has not been
configured on this server yet".

## 9. Start the notification worker

The worker delivers the outbox and queues reminders. It must run all the time next to the API.

- Local, in a second terminal:

  ```bash
  cd backend
  venv/bin/python -m app.workers.notification_worker
  ```

  You should see `Notification worker started.` If you see
  `DISCORD_BOT_TOKEN is not set`, the worker did not find the token in `backend/.env` (run it from
  the `backend/` folder).

- Lab server (systemd unit in `deploy/systemd/`):

  ```bash
  sudo systemctl enable --now prism-desk-notifications
  journalctl -u prism-desk-notifications -f
  ```

## 10. Link your account and send a test

1. In **Notifications** (sidebar, Account section) click **Link with Discord**.
2. Discord asks you to authorize the app (scope: "Access your username, avatar, and banner").
   Click **Authorize**. You are sent back to Prism Desk with "Your Discord account is now linked."
3. Click **Send test message**. Within one poll (about 15 seconds) the bot DMs you
   "Prism Desk test message".
4. The **Recent notifications and delivery status** table on the same page shows the result:
   `sent`, `retry_scheduled` (temporary problem, will retry) or `failed` (see below). Admins can see
   every row, with its last error, in the queue on **Admin → Announcements** and retry failed ones.

The test message uses the **Administrative** category, so keep that category switched on while
testing.

## Private project channels

The worker keeps one private text channel per **active** project, named after it (e.g.
`#spectral-imaging-study`). About once a minute it:

- creates the channel for any active project that has none (`@everyone` cannot see it; the bot can);
- gives every active project member with a linked Discord account access (see, post, react, threads),
  and removes members who left the project or unlinked Discord;
- renames the channel when the project is renamed;
- makes the channel **read-only** when the project is archived or deleted (history is kept; delete the
  channel by hand in Discord if you want it gone).

Members must be in the Discord server and have linked their account in Prism Desk; until then they
are retried on every pass. Server owners and admins with the Administrator permission see all
channels anyway.

Settings (optional):

```dotenv
DISCORD_PROJECT_CHANNELS=true          # false turns the feature off
DISCORD_PROJECT_CATEGORY_ID=           # a category ID to put the channels under
```

To create channels for existing projects right away instead of waiting for the worker:

```bash
cd backend
venv/bin/python -m app.services.discord_project_channels
```

## Handbook planner reminders

Reminders you create in the handbook planner are also sent to Discord as a DM at their reminder
time, if your account is linked and the **Handbook** category is on. The worker queues each
reminder up to 10 minutes ahead and holds it until its time; the DM shows the time in your own
timezone. A reminder you dismiss, delete or move before it fires is not sent at the old time (the
history shows it as `failed` with "Reminder was dismissed/deleted/moved"). If the worker was down,
reminders up to one hour late are still sent; older ones are skipped.

---

## Troubleshooting

Discord error codes appear in the worker log and in the notification's last error (Prism Desk
records the HTTP status; the JSON `code` is in Discord's response).

| Symptom | Cause | Fix |
|---|---|---|
| Discord page says **"Invalid OAuth2 redirect_uri"** | `DISCORD_REDIRECT_URI` is not exactly one of the redirects saved in the portal | Make them identical (http vs https, `localhost` vs `127.0.0.1`, port, trailing slash), save in the portal, restart the backend |
| Back in Prism Desk with **"Discord linking failed or expired"** | The link took over 10 minutes, the page was opened in a different browser, or `localhost`/`127.0.0.1` were mixed so the login cookie was missing | Use the same host for the app and the redirect URI and try again |
| **"That Discord account is already linked to another Prism Desk user"** | One Discord account can belong to only one Prism Desk user | Unlink it from the other user first |
| DMs fail with HTTP **403**, Discord code **50007** "Cannot send messages to this user" | The bot and the user share no server, or the user blocks DMs from server members, or blocked the bot | Join the lab server; enable *Allow direct messages from server members* for it. This error is permanent for that message; send a new test |
| Every send fails with HTTP **401** "401: Unauthorized" | Wrong, old or reset bot token (or it includes the word `Bot` / quotes) | Reset the token in the **Bot** tab, paste only the token into `DISCORD_BOT_TOKEN`, restart the worker |
| Channel posts fail with HTTP **403**, code **50001** "Missing Access" | The bot cannot see that channel (private channel, or not invited) | Add the bot or its role to the channel with View Channel + Send Messages |
| HTTP **403**, code **50013** "Missing Permissions" | It can see the channel but cannot post or create threads, or (project channels) it lacks Manage Channels / Manage Roles | Grant the permissions from step 4 (Server Settings → Roles → bot role) |
| HTTP **404**, code **10003** "Unknown Channel" | Wrong channel ID (e.g. a server ID pasted as a channel ID) | Copy the ID again with Developer Mode |
| Rows stay `pending` forever | The worker is not running | Start it (step 9) |
| Rows go to `retry_scheduled` with "Discord bot token is not configured" | The worker started without the token | Set `DISCORD_BOT_TOKEN` and restart the worker |
| No **Link with Discord** button | One of `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` is empty, or the backend was not restarted | Fill them in and restart |
| Announcement says channel not configured | `DISCORD_ANNOUNCEMENT_CHANNEL_ID` is empty | Set it and restart the backend |

HTTP 429 (rate limited) and 5xx errors are temporary and retried automatically with backoff.
