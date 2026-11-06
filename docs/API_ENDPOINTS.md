# Prism Desk API endpoints

Generated from the OpenAPI schema by `backend/scripts/generate_api_docs.py`.
Interactive documentation: `/docs` (Swagger UI) and `/redoc`.
Authorization rules per endpoint are described in `docs/API.md`.

## Authentication

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register | — | RegisterRequest | 201 RegisterResponse |
| `POST` | `/api/v1/auth/login` | Login | — | LoginRequest | 200 LoginResponse |
| `GET` | `/api/v1/auth/me` | Get Me | — | — | 200 LoginResponse |
| `POST` | `/api/v1/auth/logout` | Logout | — | — | 200 — |

## Administrator

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/admin/pending-users` | List Pending Users | — | — | 200 list[PendingUserResponse] |
| `POST` | `/api/v1/admin/users/{user_id}/approve` | Approve Registration | — | ApproveUserRequest | 200 AdminActionResponse |
| `POST` | `/api/v1/admin/users/{user_id}/reject` | Reject Registration | — | — | 200 AdminActionResponse |
| `GET` | `/api/v1/admin/users` | List All Users | `search`, `account_status`, `role_name`, `page`, `page_size` | — | 200 Page_UserManagementResponse_ |
| `GET` | `/api/v1/admin/users/{user_id}` | Get User Detail | — | — | 200 UserManagementResponse |
| `PATCH` | `/api/v1/admin/users/{user_id}/suspend` | Suspend Registration | — | — | 200 AdminActionResponse |
| `PATCH` | `/api/v1/admin/users/{user_id}/reactivate` | Reactivate Registration | — | — | 200 AdminActionResponse |
| `POST` | `/api/v1/admin/users/{user_id}/roles` | Assign User Role | — | RoleChangeRequest | 200 AdminActionResponse |
| `DELETE` | `/api/v1/admin/users/{user_id}/roles/{role_name}` | Remove User Role | — | — | 200 AdminActionResponse |

## Users

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/users/directory` | User Directory | `search`, `role_name`, `limit` | — | 200 list[UserSummary] |

## Audit

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/audit/logs` | Get Audit Logs | `action`, `entity_type`, `actor_id`, `page`, `page_size` | — | 200 Page_AuditLogResponse_ |

## Projects

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/projects` | List Projects | `status`, `search`, `mine`, `user_id`, `page`, `page_size` | — | 200 Page_ProjectResponse_ |
| `POST` | `/api/v1/projects` | Create Project | — | ProjectCreate | 201 ProjectResponse |
| `GET` | `/api/v1/projects/{project_id}` | Get Project | — | — | 200 ProjectResponse |
| `PATCH` | `/api/v1/projects/{project_id}` | Update Project | — | ProjectUpdate | 200 ProjectResponse |
| `DELETE` | `/api/v1/projects/{project_id}` | Soft Delete Project | — | — | 200 ProjectResponse |
| `POST` | `/api/v1/projects/{project_id}/archive-request` | Request Archive | — | ArchiveRequest | 200 ProjectResponse |
| `POST` | `/api/v1/projects/{project_id}/archive` | Archive Project | — | — | 200 ProjectResponse |
| `POST` | `/api/v1/projects/{project_id}/unarchive` | Unarchive Project | — | — | 200 ProjectResponse |
| `POST` | `/api/v1/projects/{project_id}/restore` | Restore Project | — | — | 200 ProjectResponse |
| `DELETE` | `/api/v1/projects/{project_id}/permanent` | Purge Project | — | — | 200 MessageResponse |
| `POST` | `/api/v1/projects/{project_id}/transfer-ownership` | Transfer Ownership | — | OwnershipTransferRequest | 200 ProjectResponse |
| `GET` | `/api/v1/projects/{project_id}/members` | List Members | `include_removed` | — | 200 list[ProjectMemberResponse] |
| `POST` | `/api/v1/projects/{project_id}/members` | Add Member | — | MemberAddRequest | 201 ProjectMemberResponse |
| `PATCH` | `/api/v1/projects/{project_id}/members/{member_user_id}` | Change Member Role | — | MemberRoleUpdate | 200 ProjectMemberResponse |
| `DELETE` | `/api/v1/projects/{project_id}/members/{member_user_id}` | Remove Member | — | — | 200 MessageResponse |

## Research Library

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/research/papers` | List Papers | `search`, `author`, `keyword`, `year`, `year_from`, `year_to`, `project_id`, `reading_status`, `page`, `page_size` | — | 200 Page_PaperResponse_ |
| `POST` | `/api/v1/research/papers` | Create Paper | — | PaperCreate | 201 PaperResponse |
| `GET` | `/api/v1/research/lookup` | Doi Lookup | `doi` | — | 200 DoiLookupResponse |
| `GET` | `/api/v1/research/papers/{paper_id}` | Get Paper | — | — | 200 PaperResponse |
| `PATCH` | `/api/v1/research/papers/{paper_id}` | Update Paper | — | PaperUpdate | 200 PaperResponse |
| `POST` | `/api/v1/research/papers/{paper_id}/projects` | Link Paper | — | ProjectLinkRequest | 200 PaperResponse |
| `DELETE` | `/api/v1/research/papers/{paper_id}/projects/{project_id}` | Unlink Paper | — | — | 200 MessageResponse |
| `PUT` | `/api/v1/research/papers/{paper_id}/progress` | Set Progress | — | ReadingProgressUpdate | 200 ReadingProgressResponse |
| `GET` | `/api/v1/research/progress/me` | My Progress | — | — | 200 list[ReadingProgressResponse] |
| `GET` | `/api/v1/research/projects/{project_id}/progress` | Project Progress | — | — | 200 list[ReadingProgressResponse] |
| `GET` | `/api/v1/research/papers/{paper_id}/notes` | List Notes | — | — | 200 list[NoteResponse] |
| `POST` | `/api/v1/research/papers/{paper_id}/notes` | Create Note | — | NoteCreate | 201 NoteResponse |
| `PATCH` | `/api/v1/research/notes/{note_id}` | Update Note | — | NoteUpdate | 200 NoteResponse |
| `DELETE` | `/api/v1/research/notes/{note_id}` | Delete Note | — | — | 200 MessageResponse |

## Tasks

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/tasks` | List Tasks | `scope`, `status`, `project_id`, `task_type`, `priority`, `overdue`, `search`, `page`, `page_size` | — | 200 Page_TaskResponse_ |
| `POST` | `/api/v1/tasks` | Create Task | — | TaskCreate | 201 TaskResponse |
| `GET` | `/api/v1/tasks/reviews/pending` | Pending Reviews | `project_id`, `page`, `page_size` | — | 200 Page_PendingReviewResponse_ |
| `GET` | `/api/v1/tasks/{task_id}` | Get Task | — | — | 200 TaskResponse |
| `PATCH` | `/api/v1/tasks/{task_id}` | Update Task | — | TaskUpdate | 200 TaskResponse |
| `DELETE` | `/api/v1/tasks/{task_id}` | Delete Task | — | — | 200 MessageResponse |
| `POST` | `/api/v1/tasks/{task_id}/assignees` | Add Assignees | — | AssigneesRequest | 200 TaskResponse |
| `DELETE` | `/api/v1/tasks/{task_id}/assignees/{assignee_id}` | Remove Assignee | — | — | 200 MessageResponse |
| `PATCH` | `/api/v1/tasks/assignments/{assignment_id}/status` | Change Status | — | StatusUpdate | 200 AssignmentResponse |
| `GET` | `/api/v1/tasks/assignments/{assignment_id}/submissions` | List Submissions | — | — | 200 list[SubmissionResponse] |
| `POST` | `/api/v1/tasks/assignments/{assignment_id}/submissions` | Submit | — | SubmissionCreate | 201 SubmissionResponse |
| `POST` | `/api/v1/tasks/submissions/{submission_id}/review` | Review Submission | — | ReviewCreate | 200 SubmissionResponse |

## Research Handbook

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/handbook/entries` | List Entries | `project_id`, `student_id`, `date_from`, `date_to`, `page`, `page_size` | — | 200 Page_EntryResponse_ |
| `POST` | `/api/v1/handbook/entries` | Create Entry | — | EntryCreate | 201 EntryResponse |
| `GET` | `/api/v1/handbook/entries/{entry_id}` | Get Entry | — | — | 200 EntryResponse |
| `PATCH` | `/api/v1/handbook/entries/{entry_id}` | Update Entry | — | EntryUpdate | 200 EntryResponse |
| `GET` | `/api/v1/handbook/entries/{entry_id}/versions` | Entry Versions | — | — | 200 list[VersionResponse] |
| `POST` | `/api/v1/handbook/entries/{entry_id}/comments` | Add Comment | — | CommentCreate | 201 EntryResponse |
| `GET` | `/api/v1/handbook/progress` | Progress | `project_id`, `date_from`, `date_to` | — | 200 list[ProgressDay] |
| `GET` | `/api/v1/handbook/summaries` | List Summaries | `date_from`, `date_to`, `page`, `page_size` | — | 200 Page_SummaryResponse_ |
| `POST` | `/api/v1/handbook/summaries` | Create Summary | — | SummaryCreate | 201 SummaryResponse |
| `PATCH` | `/api/v1/handbook/summaries/{summary_id}` | Update Summary | — | SummaryUpdate | 200 SummaryResponse |
| `GET` | `/api/v1/handbook/summaries/{summary_id}/versions` | Summary Versions | — | — | 200 list[VersionResponse] |

## Conferences

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/conferences` | List Conferences | `search`, `project_id`, `deadline_from`, `deadline_to`, `timing`, `include_archived_links`, `page`, `page_size` | — | 200 Page_ConferenceResponse_ |
| `POST` | `/api/v1/conferences` | Create Conference | — | ConferenceCreate | 201 ConferenceResponse |
| `GET` | `/api/v1/conferences/{conference_id}` | Get Conference | — | — | 200 ConferenceResponse |
| `PATCH` | `/api/v1/conferences/{conference_id}` | Update Conference | — | ConferenceUpdate | 200 ConferenceResponse |
| `DELETE` | `/api/v1/conferences/{conference_id}` | Delete Conference | — | — | 200 MessageResponse |
| `POST` | `/api/v1/conferences/{conference_id}/projects` | Link Conference | — | ConferenceLinkRequest | 200 ConferenceResponse |
| `POST` | `/api/v1/conferences/{conference_id}/projects/{project_id}/archive` | Archive Link | — | — | 200 MessageResponse |
| `DELETE` | `/api/v1/conferences/{conference_id}/projects/{project_id}` | Unlink Conference | — | — | 200 MessageResponse |

## Notifications (Discord)

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/notifications/discord` | Discord Status | — | — | 200 DiscordStatusResponse |
| `DELETE` | `/api/v1/notifications/discord` | Unlink Discord | — | — | 200 MessageResponse |
| `POST` | `/api/v1/notifications/discord/link` | Start Discord Link | — | — | 200 DiscordLinkStartResponse |
| `GET` | `/api/v1/notifications/discord/callback` | Discord Callback | `code`, `state`, `error` | — | 200 — |
| `GET` | `/api/v1/notifications/preferences` | Get Preferences | — | — | 200 list[PreferenceItem] |
| `PUT` | `/api/v1/notifications/preferences` | Update Preferences | — | PreferencesUpdate | 200 list[PreferenceItem] |
| `GET` | `/api/v1/notifications/history` | My Notifications | `status`, `page`, `page_size` | — | 200 Page_NotificationResponse_ |
| `GET` | `/api/v1/notifications/queue` | Notification Queue | `status`, `page`, `page_size` | — | 200 Page_NotificationResponse_ |
| `POST` | `/api/v1/notifications/{notification_id}/retry` | Retry Notification | — | — | 200 NotificationResponse |
| `POST` | `/api/v1/notifications/announcements` | Send Announcement | — | AnnouncementCreate | 200 AnnouncementResponse |

## Dashboards

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/api/v1/dashboard/admin` | Admin Dashboard | — | — | 200 AdminDashboard |
| `GET` | `/api/v1/dashboard/professor` | Professor Dashboard | — | — | 200 ProfessorDashboard |
| `GET` | `/api/v1/dashboard/student` | Student Dashboard | — | — | 200 StudentDashboard |
| `GET` | `/api/v1/dashboard/guest` | Guest Dashboard | — | — | 200 GuestDashboard |
| `GET` | `/api/v1/dashboard/projects/{project_id}` | Project Analytics | — | — | 200 ProjectAnalytics |
| `GET` | `/api/v1/dashboard/system-settings` | System Settings | — | — | 200 — |

## System

| Method | Path | Summary | Query parameters | Request body | Success response |
|---|---|---|---|---|---|
| `GET` | `/` | Root | — | — | 200 — |
| `GET` | `/health` | Health | — | — | 200 — |
| `GET` | `/health/database` | Database Health | — | — | 200 — |
