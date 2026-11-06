# Prism Desk — Audit and Implementation Plan (Phases 1–8)

Date: 2026-11-06

## 1. Audit inventory (state before this work)

### Existing and working
- FastAPI app (`backend/main.py`) with `/health`, `/health/database`, versioned router `/api/v1`.
- Auth: register (pending status), login by username/email, Argon2id hashing, server-side sessions
  (SHA-256 token hash in `user_sessions`, absolute expiry 8h, inactivity 30 min), HttpOnly SameSite=Lax cookie, logout/revocation, `/auth/me`.
- Admin: pending list, approve (assigns one non-admin role), reject, list users with search/role/status filters, suspend (revokes sessions), reactivate.
- DB (PostgreSQL 17): `users`, `roles` (4 seeded), `user_roles`, `user_sessions`, Alembic at head `seed_global_roles`. 4 users exist (3 approved, 1 pending) — preserved.
- Frontend: React 19 + Vite + Tailwind v4 + react-router 8, AuthContext, ProtectedRoute, Login, Register, Admin dashboard (pending approvals), User Management.

### Bugs / weaknesses found
1. `APP_ENV=development` turns on SQLAlchemy `echo`, which logs SQL parameters — password hashes and session-token hashes end up in logs.
2. No CSRF protection for cookie-authenticated mutations.
3. No rate limiting on login/registration.
4. Login has a user-enumeration timing difference (no hash verification when user is missing); no password rehash.
5. Rejection stores no `rejected_by` / `rejected_at`; suspension stores no actor/time.
6. No role assignment/removal API after approval; no last-administrator protection; no audit log.
7. CORS origin hard-coded to `localhost:5173` (LAN access impossible).
8. `/admin/users` not paginated.
9. `scripts/create_admin.py` uses `scalar_one_or_none()` — crashes when more than one admin exists.
10. Frontend: `/admin/dashboard` route declared twice; Login calls `navigate()` during render; login does not return users to the page they requested; User Management has no app shell/navigation; professor/student/guest dashboards are placeholders; admin dashboard statistics are partly hard-coded ("Administrator: Active").
11. No backend or frontend tests exist (`backend/tests/` empty, no Vitest).
12. `python-multipart` present although the platform forbids uploads (Phase 0 review §3.1).
13. Repository was not under version control — a local git baseline commit was created before changes.

### Missing
Phases 2–8 entirely (projects, research library, tasks, handbook, conferences, Discord/notifications, dashboards), audit logs, deployment docs.

## 2. Design decisions (conservative defaults from Phase 0 review D-01…D-14)
- Global roles stay in `roles`/`user_roles`. Project roles live in `project_members.membership_role` (`owner`, `supervisor`, `member`, `guest`) — supervising professors are members with role `supervisor` (no duplicate table).
- Guests: read-only, and only for projects an administrator/supervisor explicitly grants (membership role `guest`). Guests cannot create projects, papers, tasks, entries or conferences.
- Project management rights = Administrator, or a user with the Professor role who is the project's owner/supervisor. Student owners edit project details and may *request* archival only.
- Archived projects are read-only for ordinary activity. Deleted projects are hidden, recoverable by admins; permanent deletion is admin-only and only after the 90-day retention window. Shared papers/conferences are never deleted with a project.
- Research library metadata is visible to all approved non-guest users; private notes are visible only to their author (admins included in the restriction).
- Personal tasks are stored as tasks with `task_type='personal'` plus one assignment to the creator, so one status workflow/table serves both.
- Overall daily summaries are private to the student.
- Notifications use a transactional outbox (`notifications` table) filled inside the business transaction via a savepoint (a failure never breaks the business operation) and a separate worker process delivers to Discord with exponential backoff.
- Permission checks are centralised (`app/core/permissions.py`, `app/services/project_access.py`); the frontend gets a `capabilities` list from `/auth/me` instead of hard-coding role logic in components.

## 3. Execution order
Stage 1 audit + Phase 1 → 2 Projects → 3 Research → 4 Tasks → 5 Handbook → 6 Conferences → 7 Discord → 8 Dashboards → deployment docs.
Each stage: migration → models → schemas → services → routes → tests (pytest against an isolated `prism_test` schema, transactions rolled back) → frontend → `tsc`/build/Vitest.
