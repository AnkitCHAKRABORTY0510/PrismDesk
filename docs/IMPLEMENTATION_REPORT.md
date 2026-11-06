# Prism Desk — Implementation Report (Phases 1–8)

Date: 2026-11-06. Companion documents: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) (audit),
[DATABASE.md](DATABASE.md), [API.md](API.md) and [API_ENDPOINTS.md](API_ENDPOINTS.md),
[DEPLOYMENT.md](DEPLOYMENT.md).

The repository had no version control, so a baseline commit was made first. Each phase is a separate
local git commit (`git log --oneline`). `.env` files are ignored and were not read into any report.

## Phase 1 — Authentication and user management
**Fixed / added**
- SQL logging no longer prints parameters (password hashes, token hashes): `SQL_ECHO` is opt-in instead of tied to `APP_ENV`.
- CSRF protection: a per-session token (`sha256("prism-csrf:" + session token)`) returned by login and `/auth/me` and required in `X-CSRF-Token` on every cookie-authenticated mutation.
- Rate limiting on login and registration; timing-equalised login for unknown users; Argon2 rehash on login.
- Rejection metadata (`rejected_by`, `rejected_at`), suspension metadata, `updated_at`.
- Role assignment/removal endpoints with escalation guards: only administrators; approval cannot grant Administrator; no self-approval/rejection/suspension; you cannot remove your own Administrator role; the last active administrator and a user's last role are protected.
- Suspension revokes all sessions; reactivation revokes any survivor so a new login is required; non-approved users are rejected (401) on every request as a second line of defence.
- Append-only `audit_logs` (database trigger blocks UPDATE/DELETE) with a sanitiser that drops password/token/secret/note/content/body keys.
- CORS origins from configuration; security headers; consistent `ServiceError` → JSON error handling; paginated user list; `create_admin.py` no longer crashes when several admins exist; timestamps returned in UTC.
- Frontend: duplicate `/admin/dashboard` route removed; Login no longer navigates during render and returns users to the page they requested; any 401 signs the user out locally; CSRF token held in memory only.

**APIs:** `POST /admin/users/{id}/roles`, `DELETE /admin/users/{id}/roles/{role}`, `GET /admin/users/{id}`, `GET /audit/logs`, `GET /users/directory` (plus the existing auth/admin endpoints, now paginated where listed).
**Migration:** `a1b2c3d4e501`. **Frontend:** User Management (filters, pagination, role dialog, confirmations), Pending Registrations, Audit Logs.

## Phase 2 — Project management
- `projects` (active/archived/deleted with actor+time for each transition, archive requests) and `project_members` (owner/supervisor/member/guest, active/removed history).
- Creator becomes owner and member automatically; student owners edit details and request archival but cannot manage members or archive.
- Managers = Administrators and Professors who own/supervise the project. Archived projects are read-only for ordinary activity across all modules.
- Soft delete by managers; restore, ownership transfer and permanent delete by administrators only; permanent delete is refused during the 90-day window and keeps shared papers/conferences.
- 404 for projects a user cannot see. Notifications for project creation and membership.
- **Migration:** `a1b2c3d4e502`. **Frontend:** project list (search, status, "deleted" for admins), project detail with Overview/Members/Literature/Tasks/Handbook/Conferences/Analytics tabs, lifecycle actions with confirmation dialogs.

## Phase 3 — Research library (metadata only)
- Central `research_papers` with DOI normalisation (`https://doi.org/…` → `10.xxxx/…`) and case-insensitive unique DOI; URL duplicate check; adding a duplicate to a project links the existing record instead.
- `project_papers`, `paper_reading_progress` (per student, optional project context, NULLS NOT DISTINCT uniqueness), `research_notes` (author-only, including towards administrators).
- Search (title, abstract, venue, DOI, keywords, authors), filters (author, keyword, year, year range, project, my reading status), pagination; supervisors see member reading status (never notes). Guests only see papers linked to projects shared with them.
- **Migration:** `a1b2c3d4e503`. **Frontend:** Research Library, Paper detail (metadata, reading status, private notes), paper form, project literature tab with link-existing search.

## Phase 4 — Tasks and submissions
- `tasks` (official requires a project), `task_assignments` (independent status per student), `task_submissions` (immutable versions: text + http(s) links only), `task_reviews`.
- Workflow enforced on the server: assignee `todo↔in_progress`, `revision_required→in_progress`; submitting moves to `under_review`; only managers (not the assignee) review the latest version → `completed` or `revision_required` (feedback required). Personal tasks: `todo/in_progress/completed`, private to the creator.
- Students never see other students' assignments or submissions. Filters: scope, status, project, type, priority, overdue, search; pending review queue.
- **Migration:** `a1b2c3d4e504`. **Frontend:** task list (my/personal/project tasks, review queue), task detail with status moves, submission form, version history with reviews, review controls.

## Phase 5 — Research handbook
- `handbook_entries` (unique student+project+date), `handbook_entry_versions` (snapshot of every save), `daily_summaries` (unique student+date, private), `daily_summary_versions`, `handbook_comments` (one reply level).
- Students write entries only for active projects they belong to; only authors edit (also after comments); supervisors and administrators read and comment but cannot edit; authors and supervisors reply. Future dates refused (one day tolerance for timezones).
- Progress by date (entries and active students per day).
- **Migration:** `a1b2c3d4e505`. **Frontend:** Handbook (entries, activity strip, private summaries tab), entry form, entry detail with threaded comments and edit history.

## Phase 6 — Conferences and deadlines
- `conferences` (unique lower(name)+deadline, important dates JSON, website and CFP URLs) and `project_conferences` (active/archived associations). Duplicates are linked rather than re-created.
- Filters: search, project (optionally including archived links), deadline range, upcoming/overdue; default sort puts upcoming deadlines first. `is_overdue` and `seconds_remaining` computed server-side; the UI shows a live countdown in the viewer's timezone. Naive timestamps are rejected.
- **Migration:** `a1b2c3d4e506`. **Frontend:** Conference Tracker cards with countdowns, conference form with important dates, project conferences tab.

## Phase 7 — Discord integration and notifications
- OAuth2 linking (`identify` scope) with single-use, user-bound, hashed state; only the Discord user ID and username are stored; access tokens are discarded.
- Per-category preferences (tasks, projects, conferences, handbook, administrative).
- Transactional outbox: services enqueue inside a SAVEPOINT and swallow errors, so Discord problems never fail the business operation (tested). Unique `dedupe_key` prevents duplicates.
- Worker (`python -m app.workers.notification_worker`): `FOR UPDATE SKIP LOCKED` claiming, statuses pending → processing → sent / retry_scheduled / failed, exponential backoff, permanent-error detection, stale-processing recovery, delivery-attempt log, task-due and conference-deadline reminders. Bot token and OAuth secret are never logged or returned.
- Admin announcements (channel and/or DMs), delivery queue with manual retry. No internal chat or attachments.
- **Migration:** `a1b2c3d4e507`. **Frontend:** Notification Settings (link/unlink, preferences, delivery history), Announcements & queue page.

## Phase 8 — Dashboards and analytics
- Role dashboards from SQL aggregates (GROUP BY / FILTER / subqueries, no table scans in Python): administrator (users by status, projects by status, papers, assignment status, overdue, notification queue, upcoming conferences, recent audit activity), professor (supervised projects with completion/reviews/overdue, review queue, recent entries, deadlines, member reading progress), student (projects, assigned/personal task counts, pending submissions, completion rate, reading progress, handbook frequency, deadlines), guest (shared projects, paper count, conference deadlines).
- Project analytics for managers (completion rate, overdue, reading progress, handbook entries per week, 30-day activity, deadlines). System settings summary (non-secret values only).
- **Frontend:** single `/dashboard` with tabs for users holding several roles; legacy `/admin|professor|student|guest/dashboard` URLs redirect.

## Shared frontend
App shell (sidebar driven by backend capabilities, top bar, breadcrumbs, responsive menu), reusable
components (Button, Card, StatCard, Field/Input/Textarea/Select, SearchInput, FilterSelect, Badge/StatusBadge,
DataTable, Pagination, Modal, ConfirmDialog, EmptyState, Loading, ErrorMessage, Toast, Tabs, ProgressBar,
UserPicker), `useAsync` data hook, typed API services per module. Template CSS was moved into the base
layer so Tailwind utilities apply.

## Testing report

### Executed and passed
| Suite | Command | Result |
|---|---|---|
| Backend (PostgreSQL, isolated `prism_test` schema, migrations applied by Alembic, per-test rollback) | `cd backend && venv/bin/python -m pytest` | **91 passed**, 0 failed, 0 skipped |
| Frontend unit/component tests | `cd frontend && npm test` | **21 passed** (3 files) |
| TypeScript | `cd frontend && npx tsc -b` | no errors |
| Production build | `cd frontend && npm run build` | succeeded |
| Lint | `cd frontend && npm run lint` | no errors in `src/` (see known issues) |
| Model/migration drift | `cd backend && venv/bin/alembic check` | "No new upgrade operations detected" |
| Backup script | `scripts/backup_db.sh` | dump written and verified with `pg_restore --list` |
| Manual browser smoke test (API on the isolated test schema) | login, approve a registration, create a project, add a supervisor, open every module page | all worked; CSRF, cookies and CORS verified end to end |

Backend coverage by file: auth 14, admin 13, projects 13, research 11, notifications 12, tasks 8,
handbook 8, conferences 8, dashboard 4. Areas covered: registration (no privileged roles), login,
logout, inactivity and absolute expiry, hashed session tokens, CSRF, rate limiting, approval/rejection/
suspension/reactivation workflows, role escalation, last-admin protection, audit immutability, project
permissions and lifecycle (archive, soft delete, restore, 90-day purge), membership history, guest
read-only access, paper deduplication and associations, reading progress independence, private notes,
official/personal task privacy, the full submission/review/version workflow, archived read-only
behaviour, handbook uniqueness/history/comments/privacy, conference deduplication/filters/overdue,
notification preferences/dedup/retry/backoff/failure isolation/reminders/OAuth state, dashboard
authorization and data.

Frontend coverage: login (error and redirect), registration validation and success, protected routes
(anonymous, missing capability, allowed), role-based navigation (student/admin/guest), project list
search/filter/pagination, task submission and allowed status moves, handbook form validation,
notification preferences, date/countdown helpers.

### Failed tests
None.

### Skipped tests
None.

### Untested or partially tested
- Real Discord delivery and OAuth against discord.com (no credentials configured; covered with fakes/mocks).
- Nginx and systemd units, HTTPS and Secure cookies in production (configuration written, not installed).
- `scripts/restore_db.sh` (not run, to avoid touching the live database).
- Browser testing was a smoke test of key flows, not every page interaction; tablet layouts were checked only through responsive classes.

## Known limitations and decisions to confirm
- Guest access is per project (a `guest` membership); there is no separate feature-level guest permission table.
- Notifications are only queued for users with a linked Discord account and the category enabled; the "account approved" message therefore only reaches users who linked Discord before approval (normally none).
- Login rate limiting is in-process (single Uvicorn worker, as configured in the service file).
- Audit log retention and reminder schedule are configurable defaults (Phase 0 D-11/D-12 still open).
- System settings are read-only in the UI; values change through `backend/.env`.
- Project-wise handbook entries are visible to the author and project managers, not to other student members.
- Pre-existing stray file `frontend/@/components/ui/button.tsx` (outside `src/`, unused) still fails one lint rule; left untouched.
- `npm audit` reports advisories in the existing dependency tree; not changed in this work.
