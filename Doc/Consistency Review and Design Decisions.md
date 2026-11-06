# PRISM DESK
## Phase 0 — Consistency Review and Design Decisions

**Document:** 8 of Phase 0 — Requirements Analysis and System Design  
**Version:** 1.0  
**Purpose:** Cross-document validation before implementation  
**Status:** Review Required

---

# 1. Introduction

## 1.1 Purpose

This document reviews the seven Phase 0 documents to identify:

- Conflicting requirements.
- Missing design decisions.
- Database design weaknesses.
- Permission ambiguities.
- Incomplete workflows.
- Security and deployment concerns.

The objective is to establish a consistent specification before implementation begins.

## 1.2 Documents Reviewed

1. Software Requirements Specification (SRS).
2. User Roles and Permissions.
3. System Architecture.
4. Database Design and ER Diagram.
5. User Workflows and Process Specification.
6. Feature Specification.
7. Non-Functional Requirements.

---

# 2. Critical Issues Requiring Resolution

## Issue 1: User Roles and Project Membership

**Problem:**

The application supports multiple roles per user, but global roles and project-specific responsibilities are not sufficiently separated.

For example:
- A user may be an administrator and professor.
- A professor may supervise several projects.
- A student may participate in several projects.
- A project owner may be a student.

**Recommended decision:**

Maintain two separate permission concepts:

1. Global roles: Administrator, Professor, Student, Guest.
2. Project membership: Owner, Supervisor, Student Member, Guest Member.

Global roles determine general application permissions. Project membership determines responsibilities within individual projects.

A user may have multiple global roles but should have one clearly defined membership relationship per project.

**Required database adjustment:**

The `project_members` table should contain:
- project_id
- user_id
- membership_type
- added_by
- joined_at
- membership_status

The system must enforce uniqueness for the project/user combination unless a deliberately designed membership model requires otherwise.

**Priority:** Critical.

---

## Issue 2: Project Owner and Membership Management

**Problem:**

The documents state that a student who creates a project becomes its owner, but cannot add or remove members.

The database must consistently represent the creator as both project owner and project member.

**Recommended decision:**

- The project creator automatically becomes the project owner.
- The creator is automatically added to the project membership table.
- Only administrators and professors can add or remove members.
- Student owners can edit permitted project information.
- Student owners cannot manage membership.

The project owner relationship and membership relationship must not become inconsistent.

**Priority:** Critical.

---

## Issue 3: Professor Supervision and Project Access

**Problem:**

The documents do not fully define whether a professor can view students across all projects or only projects they supervise.

**Recommended decision:**

A professor's access to project information must be based on explicit project membership or supervision permissions.

A professor can:
- View projects they supervise.
- View project members.
- Review authorised student submissions.
- View project-wise handbook entries for authorised students.
- Comment on authorised handbook entries.

A professor cannot automatically access unrelated projects or their students' private information.

**Priority:** Critical.

---

## Issue 4: Overall Daily Summary Visibility

**Problem:**

Students maintain:
- Project-wise daily entries.
- One separate overall daily summary.

However, visibility rules for the overall summary have not been finalised.

**Recommended decision:**

Treat the overall daily summary as a private student record by default.

The student can view and edit it.

Professors and administrators should not automatically receive access to it. If laboratory supervision later requires sharing, introduce an explicit sharing permission.

This preserves the distinction between project reporting and personal daily research tracking.

**Priority:** High.

---

## Issue 5: Project Archive Permissions

**Problem:**

The project archive workflow does not specify who can archive a project.

**Recommended decision:**

- Administrators can archive any project.
- Professors can archive projects they supervise, subject to the final project authority model.
- Student owners can request archival but cannot directly archive a project.
- Archived projects retain their records.
- Archived projects become read-only for ordinary project activity unless an administrator reactivates them.

This prevents accidental modification of completed research records.

**Priority:** High.

---

## Issue 6: Project Deletion and Data Retention

**Problem:**

The application uses recoverable deletion for 90 days, but the treatment of associated records needs more detail.

**Recommended decision:**

Deleting a project must not automatically delete shared research papers.

The following records should be retained during the recovery period:
- Project details.
- Project membership history.
- Project tasks.
- Task submissions.
- Project-wise handbook records.
- Conference associations.
- Project activity history.

Restoration should recover the project and its retained relationships.

Permanent deletion must be an explicit administrative operation.

Before permanent deletion, the system must check shared references and preserve records still associated with other projects.

**Priority:** Critical.

---

## Issue 7: Task Submission Versioning

**Problem:**

The database design contains task submission records, but the relationship between submissions, revisions, and reviews needs to be explicit.

**Recommended decision:**

Use the following relationship:

- One task can have multiple student assignments.
- Each assignment belongs to one student.
- Each assignment can have multiple submission versions.
- Each submission version can have one or more review records.
- Each review belongs to an authorised reviewer.

Example:

Task A is assigned to Students X and Y.

Student X submits version 1, receives revision feedback, and submits version 2.

Student Y submits and completes their work independently.

The two students must have separate assignment and submission histories.

**Required database adjustment:**

Use separate tables:
- `tasks`
- `task_assignments`
- `task_submissions`
- `task_reviews`

Each submission must have a version number and submission timestamp.

**Priority:** Critical.

---

## Issue 8: Personal Task Ownership

**Problem:**

The existing schema does not clearly establish ownership of personal tasks.

**Recommended decision:**

Every task must have a `created_by` field.

For personal tasks:
- `created_by` identifies the student.
- The task is visible only to its creator.
- An optional project association may be used for personal organisation.
- It must not become an official assigned task automatically.

**Priority:** High.

---

## Issue 9: Research Paper Sharing

**Problem:**

Research papers are shared across projects, but the distinction between paper metadata and project associations must be preserved.

**Recommended decision:**

Maintain:

- One central `research_papers` table.
- One `paper_projects` relationship table.
- One `paper_reading_status` table per student and paper.
- One `personal_research_notes` table for private notes.

A paper linked to three projects must still have one central paper record.

Deleting a project must remove or deactivate only its project association, not the central paper record if it is still used elsewhere.

**Priority:** Critical.

---

## Issue 10: Conference Records Across Multiple Projects

**Problem:**

The current database proposal associates each conference record with one project.

However, one conference may be relevant to several projects.

**Recommended decision:**

Use:
- `conferences`
- `conference_projects`

This allows one conference record to be associated with multiple projects without duplicating conference information.

The user who adds a conference record must be recorded.

Only authorised project members should be able to add or manage the association.

**Priority:** Medium.

---

## Issue 11: Discord Integration Design

**Problem:**

Discord account linking, bot notifications, and server channel integration are related but distinct operations.

**Recommended decision:**

Use two complementary mechanisms:

1. Discord OAuth2 or an equivalent secure verification process for individual account linking.
2. A Discord bot for application notifications and configured server-channel integration.

The application must maintain a secure relationship between the Prism Desk account and Discord user ID.

Notification permissions must be checked before sending messages.

Private student information must never be sent to public channels.

**Priority:** Critical.

---

## Issue 12: Notification Reliability

**Problem:**

The application must retry failed Discord notifications, but the retry mechanism needs an explicit design.

**Recommended decision:**

Use a background notification-processing mechanism.

Suggested notification states:
- Pending.
- Processing.
- Sent.
- Failed.
- Retry Scheduled.

The notification record should include:
- Event type.
- Recipient.
- Discord destination.
- Creation timestamp.
- Attempt count.
- Last attempt timestamp.
- Delivery status.
- Error information where appropriate.

Notification delivery must not block the main database transaction.

**Priority:** High.

---

## Issue 13: Registration and Role Assignment

**Problem:**

Anyone can register, but registration approval and role assignment need a consistent initial state.

**Recommended decision:**

- New registrations receive Pending Approval status.
- Pending users cannot access protected application modules.
- Administrators review registration details.
- Administrators approve or reject accounts.
- Administrators assign approved global roles.
- Guest permissions are assigned separately.

No user should gain administrator or professor privileges through the public registration form.

**Priority:** Critical.

---

## Issue 14: Handbook Editing and Audit History

**Problem:**

Students can edit handbook entries after submission and after professor comments.

The application must preserve historical versions without preventing legitimate editing.

**Recommended decision:**

- Students can edit their own entries.
- Every edit creates a historical version.
- Professors can comment but cannot edit student entries.
- Students can reply to professor comments.
- Comments and replies remain associated with the relevant handbook entry.
- The system preserves timestamps and author information.

The edit history must not expose private research notes.

**Priority:** High.

---

# 3. Additional Technical Corrections

## 3.1 File Upload Dependency

The original development environment includes `python-multipart`.

However, Prism Desk has a strict no-file-upload policy.

**Recommendation:**

Remove `python-multipart` if no other approved application feature requires multipart form processing.

Do not implement upload endpoints or file-storage tables.

## 3.2 Database and Application Separation

PostgreSQL must remain accessible only to the backend application and authorised administrative maintenance processes.

Ordinary browser clients must communicate with FastAPI rather than directly accessing PostgreSQL.

## 3.3 Authentication

Use server-managed sessions with secure cookies.

Do not store authentication tokens or secrets in browser localStorage.

Implement session expiry, secure logout, and appropriate CSRF protection.

## 3.4 Background Processing

Discord reminders and notification retries should not be implemented as blocking operations inside ordinary API requests.

Use a background worker or another suitable processing mechanism.

## 3.5 Database Migration

All database schema changes must be managed through Alembic.

Manual production schema modifications should be avoided.

## 3.6 Application Logging

Maintain separate:
- Technical application logs.
- User activity audit records.
- Discord notification delivery logs.

Do not record passwords, tokens, or private research notes.

---

# 4. Consolidated Database Design Adjustments

The following database changes should be considered before creating production migrations.

| Existing area | Required adjustment |
|---|---|
| users and roles | Support multiple global roles |
| project_members | Explicit membership type and status |
| projects | Owner and membership consistency |
| task_assignments | Independent assignment per student |
| task_submissions | Versioned submissions |
| task_reviews | Reviewer and review history |
| tasks | Explicit created_by field |
| conferences | Separate project association table |
| research_papers | One central paper record |
| paper_projects | Many-to-many paper/project relationship |
| personal_research_notes | Strictly private student-owned records |
| daily_handbooks | Version history and project association |
| daily_summaries | Separate student-wide summary |
| handbook_comments | Comment ownership and timestamps |
| handbook_replies | Replies linked to comments |
| discord_notification_logs | Retry and delivery states |
| notification_preferences | Per-user event preferences |
| guest_project_permissions | Explicit project-level access |
| guest_feature_permissions | Explicit feature-level access |
| activity_logs | Structured, protected audit history |

These adjustments must be reflected in the final ER diagram before database migrations are generated.

---

# 5. Decisions That Must Be Finalised Before Implementation

The following points require explicit confirmation.

| ID | Decision | Recommended default |
|---|---|---|
| D-01 | Who can archive projects? | Administrator and supervising professor |
| D-02 | Who can permanently delete projects? | Administrator only |
| D-03 | Can student owners archive projects? | No; they may request archival |
| D-04 | Who can view overall daily summaries? | Student only by default |
| D-05 | Can professors access unrelated projects? | No |
| D-06 | Can one conference belong to multiple projects? | Yes |
| D-07 | Can students add conference deadlines? | Yes, if they are project members |
| D-08 | Can personal tasks be visible to professors? | No, unless explicitly shared |
| D-09 | Can administrators view private research notes? | No, by default |
| D-10 | Can archived projects be edited? | Read-only for ordinary project activity |
| D-11 | How long should audit records be retained? | Configurable; define before production |
| D-12 | How frequently should Discord reminders run? | Configurable reminder schedule |
| D-13 | Should a professor be able to remove a project owner? | No automatic owner removal; administrative transfer required |
| D-14 | Should project ownership be transferable? | Yes, through an authorised administrative operation |

---

# 6. Recommended Final System Rules

The following rules should be treated as core design principles:

1. PostgreSQL is the single source of truth for Prism Desk records.
2. Discord is the only communication and notification platform.
3. Prism Desk does not implement internal chat.
4. Prism Desk does not upload, download, or store files.
5. Users may have multiple global roles.
6. Project membership is separate from global roles.
7. Student-created projects become active immediately.
8. Student project owners cannot manage membership.
9. Research papers are stored once and shared across projects through relationships.
10. Each student has an independent task assignment and submission history.
11. Students control their own private research notes.
12. Students can edit their own handbook entries.
13. Professors can comment but cannot edit student handbook entries.
14. Overall daily summaries remain private by default.
15. Discord failures cannot interrupt core application operations.
16. Deleted projects remain recoverable for 90 days.
17. Permanent deletion is restricted to administrators.
18. All important operations must be auditable.
19. All protected operations must enforce backend permissions.
20. Database changes must be managed through Alembic.

---

# 7. Phase 0 Review Outcome

The seven original Phase 0 documents provide a strong functional and architectural foundation.

However, the following areas need to be finalised before implementation:

- Project permissions and ownership.
- Professor supervision scope.
- Overall daily summary visibility.
- Project archival permissions.
- Task submission versioning.
- Conference-to-project relationships.
- Discord notification processing.
- Audit and data-retention policies.

The database ER diagram should be revised after these decisions are approved.

**Recommended next phase:** Phase 1 — Technical Environment and Database Preparation.

Phase 1 should begin with:
1. Confirming PostgreSQL installation.
2. Creating the Prism Desk database and database user.
3. Configuring backend database connectivity.
4. Establishing Alembic migrations.
5. Revising the logical ER diagram.
6. Creating the initial database schema.
7. Testing database connectivity and persistence.

No complete application implementation should begin until the foundational database and authentication architecture have been validated.