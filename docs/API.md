# Prism Desk — API Documentation

- Base path: `/api/v1`. Interactive docs: `/docs` (Swagger) and `/redoc` (toggle with `API_DOCS_ENABLED`).
- The complete endpoint table, with request and response schema names, is generated from OpenAPI into
  [`API_ENDPOINTS.md`](API_ENDPOINTS.md) (`cd backend && python -m scripts.generate_api_docs`).
- Errors use `{"detail": "<message>"}`; validation errors (422) use FastAPI's list format.
- Lists are paginated: `?page=1&page_size=20` (max 100) → `{"items": [...], "total", "page", "page_size"}`.
- No endpoint accepts or returns files. Papers, submissions and handbook references are text and `http(s)` links.

## Authentication model
- `POST /auth/login` sets an **HttpOnly, SameSite=Lax** `prism_session` cookie (Secure in production)
  and returns the user, their `roles`, `capabilities` and a `csrf_token`.
- Every state-changing request (POST/PUT/PATCH/DELETE) authenticated by the cookie must send
  `X-CSRF-Token: <csrf_token>`. The token is derived from the session and also returned by `GET /auth/me`.
- Sessions expire after `SESSION_EXPIRE_HOURS` (8 h) or `SESSION_INACTIVITY_MINUTES` (30 min) of inactivity.
  Suspension revokes all sessions; reactivated users must log in again.
- `POST /auth/login` (10/5 min per IP) and `POST /auth/register` (5/5 min per IP) are rate limited (429).
- Unauthenticated → 401. Authenticated but not allowed → 403. Project-scoped resources the caller
  cannot see return 404 so IDs are not disclosed.

## Global capabilities (from `backend/app/core/permissions.py`)
| Capability | Admin | Professor | Student | Guest |
|---|:-:|:-:|:-:|:-:|
| users.manage, audit.view, settings.view, announcements.send, projects.view_all | ✓ | | | |
| projects.create, research.view, research.create, conferences.create, tasks.view, handbook.view | ✓ | ✓ | ✓ | |
| tasks.create_official, tasks.review, handbook.review | ✓ | ✓ | | |
| tasks.personal, handbook.write, research.track_progress | | | ✓ | |
| projects.view (own memberships) | ✓ | ✓ | ✓ | ✓ |
| notifications.manage_own | ✓ | ✓ | ✓ | ✓ |

Users can hold several roles; capabilities are the union.

## Project-level rules (from `backend/app/services/project_access.py`)
| Right | Who |
|---|---|
| View project | Administrators; active members (owner, supervisor, member, guest). Deleted projects: administrators only |
| Manager ("supervisor") | Administrators, or users with the Professor role whose membership is owner/supervisor |
| Edit details | Managers and the owner, while the project is active |
| Contribute (papers, conferences, entries) | Administrators, owner, supervisors, members — active projects only |
| Manage members | Managers, active projects only (student owners cannot) |
| Request archival | Owner who is not a manager |
| Archive / restore from archive | Managers |
| Soft delete | Managers |
| Restore deleted / permanent delete / transfer ownership | Administrators (permanent delete only after 90 days) |

## Endpoint authorization summary
| Module | Endpoints | Authorization |
|---|---|---|
| Auth | `POST /auth/register`, `POST /auth/login` | Public (rate limited). Registration never assigns roles |
| | `GET /auth/me`, `POST /auth/logout` | Session (logout also needs CSRF when the session is valid) |
| Admin | `/admin/pending-users`, `/admin/users[/{id}]`, approve, reject, suspend, reactivate, `POST/DELETE /admin/users/{id}/roles` | Administrator. Cannot approve/reject/suspend self, remove own Administrator role, remove a user's last role, or remove/suspend the last active administrator |
| Users | `GET /users/directory` | Administrator or Professor (no emails exposed) |
| Audit | `GET /audit/logs` | `audit.view` (read-only; no write routes exist) |
| Projects | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `archive-request`, `archive`, `unarchive`, `restore`, `DELETE /permanent`, `transfer-ownership`, `/members[...]` | Project-level rules above. `?status=deleted` and `?user_id=` (other users) are administrator-only |
| Research | `GET/POST /research/papers`, `GET/PATCH /research/papers/{id}` | Lab members see the library; guests only papers of their projects. Edit: adder, Professor or Administrator. Duplicate DOI/URL → 409, or linked to `project_id` when given |
| | `POST/DELETE /research/papers/{id}/projects[/{project_id}]` | Link: project contributors. Unlink: managers or the user who linked it |
| | `PUT /research/papers/{id}/progress`, `GET /research/progress/me` | Students (own progress only) |
| | `GET /research/projects/{id}/progress` | Project managers (statuses only, never notes) |
| | `/research/papers/{id}/notes`, `/research/notes/{id}` | Author only — administrators included in the restriction |
| Tasks | `GET/POST /tasks`, `GET/PATCH/DELETE /tasks/{id}`, `/tasks/{id}/assignees` | Official: create/edit/assign by project managers; assignees must be student members. Personal: Students, visible only to the creator |
| | `PATCH /tasks/assignments/{id}/status` | Assignee only; allowed moves: todo↔in_progress, revision_required→in_progress (personal: todo/in_progress/completed) |
| | `GET/POST /tasks/assignments/{id}/submissions` | Read: assignee or managers. Submit: assignee (text + links), moves to under_review, new version |
| | `POST /tasks/submissions/{id}/review` | Managers (not the assignee); latest version under review only; approve → completed, revision → revision_required |
| | `GET /tasks/reviews/pending` | Managers' queue |
| Handbook | `GET/POST /handbook/entries`, `GET/PATCH /handbook/entries/{id}`, `/versions` | Students write one entry per project per day for projects they belong to; only the author edits; managers read |
| | `POST /handbook/entries/{id}/comments` | Top-level: managers. Replies: the entry's author or managers |
| | `GET /handbook/progress` | Own entries plus supervised projects |
| | `/handbook/summaries[...]` | Author only (private) |
| Conferences | `GET/POST /conferences`, `GET/PATCH/DELETE /conferences/{id}`, `/conferences/{id}/projects[...]` | View: lab members (guests: linked to their projects). Create: `conferences.create`; link: project contributors; edit: adder/Professor/Admin; delete: Admin, or the adder when no active links |
| Notifications | `GET/DELETE /notifications/discord`, `POST /notifications/discord/link`, `GET /notifications/discord/callback` | Own account; OAuth state is single-use, user-bound, 10-minute expiry |
| | `GET/PUT /notifications/preferences`, `GET /notifications/history` | Own settings and delivery status |
| | `GET /notifications/queue`, `POST /notifications/{id}/retry`, `POST /notifications/announcements` | Administrators |
| Dashboard | `GET /dashboard/admin` · `/professor` · `/student` · `/guest` | `dashboard.<role>` capability |
| | `GET /dashboard/projects/{id}` | Project managers |
| | `GET /dashboard/system-settings` | Administrators (non-secret values only) |
| System | `GET /health`, `GET /health/database` | Public health checks |
