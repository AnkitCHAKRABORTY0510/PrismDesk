# Prism Desk — API Documentation

- Base path: `/api/v1`. Interactive docs: `/docs` (Swagger) and `/redoc` (toggle with `API_DOCS_ENABLED`).
- The complete endpoint table, with request and response schema names, is generated from OpenAPI into
  [`API_ENDPOINTS.md`](API_ENDPOINTS.md) (`cd backend && python -m scripts.generate_api_docs`).
- Errors use `{"detail": "<message>"}`; validation errors (422) use FastAPI's list format.
- Unexpected server errors return 500 `{"detail": "The server hit an unexpected error…"}` with CORS headers, so browsers can read them; details go to the backend log.
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
| projects.create, research.view, research.create, research.track_progress, conferences.create, journals.view, journals.create, tasks.view, handbook.view | ✓ | ✓ | ✓ | |
| tasks.create_official, tasks.review, handbook.review | ✓ | ✓ | | |
| tasks.personal, handbook.write | | | ✓ | |
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
| | `GET /projects/{id}/repo-links` | Anyone who can view the project (guests included). Each item: `id, project_id, url, label, added_by, added_by_username, created_at, can_remove` |
| | `POST /projects/{id}/repo-links` | Active members (owner/supervisor/member) or managers, project must be active (archived → 403, guests → 403). Body `{"url": "https://github.com/owner/repo[/…]", "label": "optional, ≤100"}`. URL must be `https://github.com/<owner>/<repo>`; it is normalised (no `www.`, query, fragment, trailing slash or `.git`). Duplicate → 409. Audited as `project.repo_link_added` |
| | `DELETE /projects/{id}/repo-links/{link_id}` | The member who added it, or a project manager; project must be active. Audited as `project.repo_link_removed` |
| Research | `GET/POST /research/papers`, `GET/PATCH /research/papers/{id}` | Lab members see the library; guests only papers of their projects. Edit: adder, Professor or Administrator. Duplicate DOI/URL → 409, or linked to `project_id` when given |
| | `GET /research/lookup?q=` | `research.create`; rate-limited. Suggests metadata (nothing saved) for a DOI, arXiv ID/link, paper web page or title via Crossref / arXiv / OpenAlex / page meta tags. Returns `matched_by`, `source`, `existing_paper_id` (duplicate). 404 not found, 422 bad or private link, 502/504 upstream error/timeout. `?doi=` still works as a strict DOI lookup |
| | `POST/DELETE /research/papers/{id}/projects[/{project_id}]` | Link: project contributors. Unlink: managers or the user who linked it |
| | `PUT /research/papers/{id}/progress`, `GET /research/progress/me` | `research.track_progress` (Students, Professors, Administrators); each user reads and sets only their own status. Body `{"status": "not_started" \| "reading" \| "completed", "project_id": null}` — shown in the UI as To read / Reading / Completed. The UI writes the library-wide status (`project_id: null`) |
| | `GET /research/projects/{id}/progress` | Project managers (statuses only, never notes) |
| | `/research/papers/{id}/notes`, `/research/notes/{id}` | Author only — administrators included in the restriction |
| Tasks | `GET/POST /tasks`, `GET/PATCH/DELETE /tasks/{id}`, `/tasks/{id}/assignees` | Official: create/edit/assign by project managers; assignees must be student members. Personal: Students, visible only to the creator |
| | `PATCH /tasks/assignments/{id}/status` | Assignee only; allowed moves: todo↔in_progress, revision_required→in_progress (personal: todo/in_progress/completed) |
| | `GET/POST /tasks/assignments/{id}/submissions` | Read: assignee or managers. Submit: assignee (text + links), moves to under_review, new version |
| | `POST /tasks/submissions/{id}/review` | Managers (not the assignee); latest version under review only; approve → completed, revision → revision_required |
| | `GET /tasks/reviews/pending` | Managers' queue |
| | `POST /tasks` with `task_type: "reminder"` | Reminders to other users. Body: `title`, optional `description`, `due_at`, `assignee_ids` (recipients, required) and `related_task_id` (an official task) or `project_id`. Project managers (Professor/Administrator) may remind any active owner/supervisor/member of the project, with or without a related task. Students may only remind the project's professors (owner/supervisor members with the Professor role) about an official task assigned to them. Guests and archived projects → 403; ineligible recipients → 400. Each recipient gets a private Discord DM (`task.reminder`, category `tasks`, respects opt-outs/linked account); audited as `task.reminder_sent`. Reminders are visible only to the sender and recipients, stay out of the dashboard pipelines/deadlines, and recipients move them `todo↔completed` via the status endpoint |
| | `GET /tasks/reminder-recipients?related_task_id=…` or `?project_id=…` | Who the caller may remind (`[{user, membership_role}]`), same rules as above |
| | `GET /tasks?scope=reminders` | Reminders the caller received or sent. Task responses also include `created_by_user`, `related_task_id`, `related_task_title`. Assigning official work (`task.assigned`) also sends a private Discord DM naming who assigned it |
| Handbook | `GET/POST /handbook/entries`, `GET/PATCH /handbook/entries/{id}`, `/versions` | Students write one entry per project per day for projects they belong to; only the author edits; managers read |
| | `POST /handbook/entries/{id}/comments` | Top-level: managers. Replies: the entry's author or managers |
| | `GET /handbook/progress` | Own entries plus supervised projects |
| | `/handbook/summaries[...]` | Author only (private). Never returned to supervisors or administrators |
| | `GET/POST /handbook/shared-notes`, `GET/PATCH /handbook/shared-notes/{id}`, `/versions` | `handbook.view` (guests 403). The student's note for one day, written for supervisors (one per student per date; 409 on a duplicate). Write and edit: the student (`handbook.write`), today or earlier only. Read: the student, and managers (owner/supervisor, or Administrator) of a non-deleted project where the student is an active owner or member; anyone else gets 404. List params: `date_from`, `date_to`, `student_id`, paging. Each save adds a version |
| | `POST /handbook/shared-notes/{id}/comments` | Top-level: those managers, on an active project. Replies: the student or those managers. Notifies the student (and the parent comment's author) through the Discord outbox |
| | `GET /handbook/planner?date_from&date_to` | `handbook.view` (guests 403). The caller's own pins, to-dos and reminders in the range (max 400 days; end before start → 400) as `{pins, todos, reminders}` |
| | `POST /handbook/pins`, `PATCH/DELETE /handbook/pins/{id}` | `handbook.view`; owner only (another user's id → 404). `pin_date`, `label` (1–120), `category` = deadline/meeting/milestone/idea/other, optional `note`. Future dates allowed |
| | `POST /handbook/todos`, `PATCH/DELETE /handbook/todos/{id}`, `GET /handbook/todos/open?limit=` | `handbook.view`; owner only. `todo_date`, `text` (1–500); PATCH sets `text`, `done` (stamps `done_at`) or moves `todo_date`. `open` lists unfinished to-dos by date (limit 1–100, default 20) |
| | `POST /handbook/todos/reorder`, `POST /handbook/todos/carry-forward` | `handbook.view`; owner only. Reorder: `{todo_date, ids}` with every to-do of that day exactly once (else 400). Carry forward: `{from_date, to_date}` moves that day's unfinished to-dos to the end of a later day's list |
| | `POST /handbook/reminders`, `PATCH/DELETE /handbook/reminders/{id}`, `GET /handbook/reminders/upcoming?limit=` | `handbook.view`; owner only. `reminder_date` (local day), `remind_at` (ISO datetime), `note` (1–500); PATCH `dismissed: true/false`; moving `remind_at` re-arms a dismissed reminder. `upcoming`: undismissed reminders due within the last 7 days or later. Delivered in-app and as browser notifications (not via Discord) |
| Conferences | `GET/POST /conferences`, `GET/PATCH/DELETE /conferences/{id}`, `/conferences/{id}/projects[...]` | View: lab members (guests: linked to their projects). Create: `conferences.create`; link: project contributors; edit: adder/Professor/Admin; delete: Admin, or the adder when no active links |
| | `GET /conferences/catalog` | Any logged-in user. Browses the public ccf-deadlines list (not stored in the database). Params: `q`, `category`, `core_rank`, `ccf_rank`, `topic` (a tag id — architecture, embedded, vlsi, low_power, reliability, security, ai, systems — or `prism` for the PRISM focus preset), `scope` = lab (default)/all, `upcoming_only` (default true), `sort` = deadline (default)/name, `limit` (1–200, default 50), `offset`. Items say `in_my_list` / `my_conference_id`; the response carries the source credit, `fetched_at`, `stale`, categories and topics |
| | `POST /conferences/catalog/refresh` | Any logged-in user. Re-downloads the list (cached 12 h in memory and on disk; after a failed download the saved copy is served with `stale: true`) |
| | `POST /conferences/catalog/{key}/add` | `conferences.create` (guests 403). Optional body `{project_id}`. 201 when created; 200 with `linked_existing: true` when the same "ACRONYM YEAR" is already in the caller's list. 404 unknown key; 400 when the deadline is TBD or has passed |
| Journals | `GET /journals`, `POST /journals`, `GET/PATCH/DELETE /journals/{id}` | Own list only (another user's id → 404). List params: `search`, `deadline` = special/rolling, `project_id`, paging. Create: `journals.create` (guests 403) |
| | `GET /journals/catalog` | Any logged-in user. Params: `q`, `domain` = lab (default)/architecture/electronics/ai/cs_other, `quartile` = Q1–Q4, `sort` = sjr (default)/relevance/h_index/title/citations, `limit` (1–100, default 25), `offset`. `total_is_estimate` says whether `total` is exact; `ranking_available` is false (with a note) when no SJR file is present; items say `in_my_list` / `my_journal_id` |
| | `POST /journals/catalog/refresh` | Any logged-in user. Reloads the SJR ranking snapshot; reports `ranking_available`, `total`, `fetched_at`, `stale`, `note` |
| | `POST /journals/catalog/{issn}/add` | `journals.create` (guests 403). Optional body `{project_id}`. 201 created; 200 with `linked_existing: true` when already in the caller's list; 404 unknown ISSN |
| Notifications | `GET/DELETE /notifications/discord`, `POST /notifications/discord/link`, `GET /notifications/discord/callback` | Own account; OAuth state is single-use, user-bound, 10-minute expiry |
| | `GET/PUT /notifications/preferences`, `GET /notifications/history` | Own settings and delivery status |
| | `GET /notifications/queue`, `POST /notifications/{id}/retry`, `POST /notifications/announcements` | Administrators |
| Dashboard | `GET /dashboard/admin` · `/professor` · `/student` · `/guest` | `dashboard.<role>` capability. Project summaries include `assignment_counts` (per status), `members` (first 5: `user_id, username, full_name, membership_role`) and `repo_links` (first 3: `url, label`). Student adds `reading_list` (≤8 papers with the caller's status), `handbook_days` (`[{day, count}]`, last 12 weeks) and `handbook_streak`; its `reading_progress` counts papers linked to the student's projects or tracked by them, untouched papers = `not_started`. Professor adds `my_reading`, `reading_list` and `member_reading` (`[{user_id, username, full_name, counts, total}]`); its `reading_progress` excludes the professor's own rows. Admin adds `my_reading` and `reading_list` |
| | `GET /dashboard/projects/{id}` | Project managers |
| | `GET /dashboard/system-settings` | Administrators (non-secret values only) |
| System | `GET /health`, `GET /health/database` | Public health checks |

## External data sources (catalogs)
| Source | Used for | Licence / credit |
|---|---|---|
| [ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines) | Conference catalog (`/conferences/catalog`) | MIT; credited in the UI and in each catalog response |
| [SCImago Journal Rank](https://www.scimagojr.com) CSV | Journal quartiles, SJR and h-index (`/journals/catalog`) | Free use with attribution; credited in the UI. Saved by hand to `backend/data/scimagojr.csv` |
| [OpenAlex](https://openalex.org) | Journal metadata and search (`/journals/catalog`), paper lookup (`/research/lookup`) | CC0. Optional `OPENALEX_API_KEY` for a higher rate limit |
