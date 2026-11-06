# PRISM DESK
## Database Design and Entity Relationship (ER) Diagram

**Project:** Prism Desk  
**Laboratory:** PRISM Laboratory  
**Document:** Database Design Specification  
**Version:** 1.0  
**Phase:** Phase 0 – Requirements Analysis and System Design  
**Database:** PostgreSQL  
**ORM:** SQLAlchemy  
**Migration Tool:** Alembic  
**Status:** Initial Database Design Baseline

---

# 1. Introduction

## 1.1 Purpose

This document defines the database structure of Prism Desk.

It describes:

- Database entities.
- Database tables.
- Primary keys.
- Foreign keys.
- Relationships.
- Data organisation.
- Access-control relationships.
- Data retention.
- Database constraints.

The database will be implemented using PostgreSQL.

SQLAlchemy will be used for database operations, while Alembic will manage database migrations.

## 1.2 Database Design Objectives

The database must:

1. Support four user roles.
2. Support multiple administrators and professors.
3. Allow students to participate in multiple projects.
4. Allow multiple professors to supervise one project.
5. Maintain project-specific tasks and handbook records.
6. Maintain a common laboratory research library.
7. Allow research papers to be associated with multiple projects.
8. Support individual submissions for multi-student tasks.
9. Maintain personal research notes privately.
10. Maintain professor comments on handbook entries.
11. Track conference submission deadlines.
12. Maintain Discord account associations.
13. Store notification preferences.
14. Maintain activity and audit history.
15. Support project archiving and safe deletion.
16. Avoid storing files and attachments.

---

# 2. Database Technology

| Component | Technology |
|---|---|
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Driver | Psycopg |
| Migration Management | Alembic |
| Backend | FastAPI |
| Data Validation | Pydantic |

## 2.1 Database Name

```text
prism_desk
```

## 2.2 Database User

```text
prism_user
```

The database should be accessible only to the backend application.

Laboratory users must never connect directly to PostgreSQL.

---

# 3. Database Architecture Overview

The database will be divided into logical groups.

| Group | Purpose |
|---|---|
| User Management | Accounts, roles and registration |
| Project Management | Projects and memberships |
| Research Library | Research papers and resources |
| Task Management | Tasks, assignments and submissions |
| Handbook Management | Daily entries, comments and edit history |
| Conference Management | Conferences and submission deadlines |
| Discord Integration | Discord account and channel mapping |
| Notifications | User notification preferences |
| Guest Permissions | Configurable guest access |
| Audit Management | Important application activities |
| Authentication | Sessions and password reset records |

---

# 4. Entity Relationship Diagram

The following diagram shows the major relationships between database entities.

```text
                         USERS
                           |
              --------------------------
              |            |           |
              |            |           |
            ROLES      PROJECTS     DISCORD
              |        (OWNER)       ACCOUNTS
              |            |
         USER_ROLES        |
              |            |
              |       PROJECT_MEMBERS
              |            |
              |       ---------------
              |       |             |
              |     TASKS        HANDBOOK
              |       |             |
              |  TASK_ASSIGNMENTS   |
              |       |       HANDBOOK_COMMENTS
              |  TASK_SUBMISSIONS   |
              |                     |
              |              HANDBOOK_REPLIES
              |
              |
        RESEARCH PAPERS
              |
        PAPER_PROJECTS
              |
           PROJECTS
              |
       CONFERENCES
              |
          PROJECTS


USERS
  |
  |---------------- NOTIFICATION_PREFERENCES
  |
  |---------------- READING_STATUS
  |
  |---------------- PERSONAL_RESEARCH_NOTES
  |
  |---------------- DAILY_SUMMARIES
  |
  |---------------- AUDIT_LOGS
  |
  |---------------- USER_SESSIONS
  |
  |---------------- GUEST_PERMISSIONS
```

The detailed relationships are defined in the following sections.

---

# 5. User Management Tables

## 5.1 users

Stores information about all Prism Desk users.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| username | VARCHAR(50) | Unique username |
| email | VARCHAR(255) | Unique email |
| password_hash | TEXT | Hashed password |
| full_name | VARCHAR(150) | User's name |
| account_status | VARCHAR(30) | Pending, Approved, Rejected, Deactivated |
| is_active | BOOLEAN | Account availability |
| created_at | TIMESTAMPTZ | Registration date |
| updated_at | TIMESTAMPTZ | Last update |
| approved_by | UUID | Administrator who approved |
| approved_at | TIMESTAMPTZ | Approval date |

**Primary Key:** id

**Unique Constraints:**
- username
- email

**Foreign Key:**
- approved_by → users.id

A user cannot access protected application functionality until their account is approved.

## 5.2 roles

Stores available system roles.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| role_name | VARCHAR(50) | Role name |
| description | TEXT | Role description |

Initial roles:

- Administrator
- Professor
- Student
- Guest

## 5.3 user_roles

Associates users with their assigned roles.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | User reference |
| role_id | UUID | Role reference |
| assigned_by | UUID | Assigning administrator |
| assigned_at | TIMESTAMPTZ | Assignment date |

This table supports multiple roles for one user.

For example, an administrator may also have professor privileges.

**Relationships:**

- One user can have multiple roles.
- One role can belong to multiple users.

## 5.4 user_sessions

Stores authenticated user sessions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | User reference |
| session_token_hash | TEXT | Hashed session identifier |
| created_at | TIMESTAMPTZ | Session creation |
| last_activity_at | TIMESTAMPTZ | Last activity |
| expires_at | TIMESTAMPTZ | Expiration time |
| revoked_at | TIMESTAMPTZ | Session revocation |

This table supports automatic logout after inactivity.

Raw session tokens must not be stored.

## 5.5 password_reset_tokens

Stores password-reset information.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | User reference |
| token_hash | TEXT | Hashed reset token |
| expires_at | TIMESTAMPTZ | Expiration |
| used_at | TIMESTAMPTZ | Token usage |
| created_at | TIMESTAMPTZ | Creation date |

Reset tokens must expire and must not be reusable.

---

# 6. Project Management Tables

## 6.1 projects

Stores all research projects.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| title | VARCHAR(255) | Project title |
| description | TEXT | Project description |
| objectives | TEXT | Research objectives |
| owner_id | UUID | Project creator and owner |
| status | VARCHAR(30) | Active, Archived, Deleted |
| start_date | DATE | Project start |
| expected_end_date | DATE | Expected completion |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |
| archived_at | TIMESTAMPTZ | Archive date |
| deleted_at | TIMESTAMPTZ | Deletion date |
| deleted_by | UUID | Administrator who deleted |
| purge_after | TIMESTAMPTZ | Recovery expiration |

**Foreign Keys:**

- owner_id → users.id
- deleted_by → users.id

The project creator automatically becomes its owner.

A student-created project becomes active immediately.

## 6.2 project_members

Maintains project membership.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| project_id | UUID | Project reference |
| user_id | UUID | User reference |
| membership_status | VARCHAR(30) | Active, Removed |
| added_by | UUID | User who added member |
| joined_at | TIMESTAMPTZ | Joining date |
| removed_at | TIMESTAMPTZ | Removal date |

**Relationships:**

- One project can have multiple members.
- One user can belong to multiple projects.

A unique constraint should prevent duplicate active memberships.

Only administrators and professors can add or remove project members.

Project ownership is maintained separately from membership.

## 6.3 project_invitations

Optional table for managing future project invitations.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| project_id | UUID | Project reference |
| invited_user_id | UUID | Invited user |
| invited_by | UUID | Inviting user |
| status | VARCHAR(30) | Pending, Accepted, Rejected |
| created_at | TIMESTAMPTZ | Invitation date |
| responded_at | TIMESTAMPTZ | Response date |

This table is useful if project invitations are introduced.

---

# 7. Research Library Tables

The Research Library will contain a common laboratory collection and project-specific collections.

A research paper should be stored only once.

## 7.1 research_papers

Stores research paper metadata and external URLs.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| title | TEXT | Research paper title |
| authors | TEXT | Author information |
| publication_year | INTEGER | Publication year |
| journal_name | VARCHAR(255) | Journal |
| conference_name | VARCHAR(255) | Conference |
| doi | VARCHAR(255) | DOI |
| paper_url | TEXT | External paper link |
| abstract | TEXT | Paper abstract |
| research_area | VARCHAR(255) | Research topic |
| visibility | VARCHAR(30) | Laboratory or Project |
| added_by | UUID | User who added paper |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |

**Foreign Key:**

- added_by → users.id

No PDF or document will be stored.

## 7.2 paper_projects

Connects research papers to projects.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| paper_id | UUID | Research paper |
| project_id | UUID | Associated project |
| added_by | UUID | User who associated it |
| created_at | TIMESTAMPTZ | Association date |

**Relationships:**

- One paper can belong to multiple projects.
- One project can contain multiple papers.

A unique constraint should prevent duplicate paper-project associations.

## 7.3 paper_reading_status

Stores individual student reading progress.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| paper_id | UUID | Paper reference |
| user_id | UUID | Student reference |
| status | VARCHAR(30) | Not Started, Reading, Completed |
| updated_at | TIMESTAMPTZ | Last update |

A student has one current reading-status record per paper.

Professors can view reading status within their authorised project supervision scope.

## 7.4 personal_research_notes

Stores private student notes associated with papers.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| paper_id | UUID | Paper reference |
| user_id | UUID | Note owner |
| note_text | TEXT | Personal notes |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |

**Privacy requirement:**

Only the note owner can read or modify these notes.

Administrators and professors cannot access them by default.

---

# 8. Task Management Tables

Task management requires separate task definitions and student assignments.

This is necessary because one professor can assign a single task to multiple students while requiring individual submissions.

## 8.1 tasks

Stores official and personal task definitions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| title | VARCHAR(255) | Task title |
| description | TEXT | Task description |
| task_type | VARCHAR(30) | Official or Personal |
| project_id | UUID | Associated project |
| created_by | UUID | Task creator |
| priority | VARCHAR(30) | Low, Medium, High |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |
| due_date | TIMESTAMPTZ | Deadline |

Personal tasks belong to their student creator.

Official tasks belong to a project.

## 8.2 task_assignments

Associates tasks with individual students.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| task_id | UUID | Task reference |
| student_id | UUID | Assigned student |
| assigned_by | UUID | Assigning user |
| status | VARCHAR(30) | Task status |
| assigned_at | TIMESTAMPTZ | Assignment date |
| completed_at | TIMESTAMPTZ | Completion date |

Task status values:

- To Do
- In Progress
- Under Review
- Revision Required
- Completed

A task assigned to three students will have three assignment records.

Each assignment will maintain its own status.

## 8.3 task_submissions

Stores individual task submissions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| assignment_id | UUID | Task assignment |
| submission_text | TEXT | Student response |
| submitted_at | TIMESTAMPTZ | Submission date |
| updated_at | TIMESTAMPTZ | Last update |

The initial design supports text-based submissions.

## 8.4 task_submission_links

Stores external links included in submissions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| submission_id | UUID | Submission reference |
| url | TEXT | External URL |
| description | TEXT | Link description |
| created_at | TIMESTAMPTZ | Creation date |

Multiple external links can be associated with one submission.

No file attachment field or file-storage table will be created.

## 8.5 task_reviews

Stores professor feedback on submissions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| submission_id | UUID | Submission reference |
| reviewer_id | UUID | Professor or administrator |
| feedback | TEXT | Review comments |
| decision | VARCHAR(30) | Approved or Revision Required |
| created_at | TIMESTAMPTZ | Review date |

A submission may have multiple review records over time.

---

# 9. Daily Research Handbook Tables

The handbook will support separate project-wise entries and one overall daily summary.

## 9.1 daily_handbooks

Stores project-wise daily research entries.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| student_id | UUID | Student reference |
| project_id | UUID | Project reference |
| entry_date | DATE | Research date |
| activities | TEXT | Activities performed |
| work_completed | TEXT | Completed work |
| problems | TEXT | Problems encountered |
| observations | TEXT | Research observations |
| next_steps | TEXT | Planned activities |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |

A student can create one project-wise entry per project per day.

The database should enforce uniqueness on:

```text
(student_id, project_id, entry_date)
```

## 9.2 daily_summaries

Stores the overall daily research summary.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| student_id | UUID | Student reference |
| summary_date | DATE | Summary date |
| summary_text | TEXT | Overall daily summary |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |

Uniqueness constraint:

```text
(student_id, summary_date)
```

## 9.3 handbook_comments

Stores professor comments on student handbook entries.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| handbook_id | UUID | Handbook entry |
| professor_id | UUID | Comment author |
| comment_text | TEXT | Comment |
| created_at | TIMESTAMPTZ | Comment date |
| updated_at | TIMESTAMPTZ | Last update |

Professors can comment but cannot modify student entries.

## 9.4 handbook_replies

Stores student replies to professor comments.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| comment_id | UUID | Parent comment |
| student_id | UUID | Reply author |
| reply_text | TEXT | Reply |
| created_at | TIMESTAMPTZ | Reply date |
| updated_at | TIMESTAMPTZ | Last update |

## 9.5 handbook_edit_history

Maintains a record of changes to submitted handbook entries.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| handbook_id | UUID | Handbook entry |
| edited_by | UUID | Student who edited |
| previous_content | JSONB | Previous entry content |
| edited_at | TIMESTAMPTZ | Edit timestamp |

Students can continue editing their own entries.

The system should preserve historical versions.

Professors cannot modify student entries.

---

# 10. Conference Management Tables

## 10.1 conferences

Stores conference and Call for Papers information.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| conference_name | VARCHAR(255) | Conference name |
| official_url | TEXT | Conference website |
| cfp_url | TEXT | Call for Papers link |
| submission_deadline | TIMESTAMPTZ | Submission deadline |
| description | TEXT | Conference information |
| project_id | UUID | Associated project |
| added_by | UUID | User who added it |
| created_at | TIMESTAMPTZ | Creation date |
| updated_at | TIMESTAMPTZ | Last update |

Any project member can add conference deadlines.

The project owner and professors can also manage conference records according to their permissions.

The submission deadline must include its timezone so that reminders are calculated correctly.

---

# 11. Discord Integration Tables

## 11.1 discord_accounts

Maps Prism Desk users to Discord accounts.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Prism Desk user |
| discord_user_id | VARCHAR(100) | Discord user identifier |
| linked_at | TIMESTAMPTZ | Linking date |
| is_active | BOOLEAN | Link status |

Discord user IDs must be unique.

The system should validate account linking.

## 11.2 discord_channels

Stores Discord channel associations.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| project_id | UUID | Associated project |
| discord_guild_id | VARCHAR(100) | Discord server ID |
| discord_channel_id | VARCHAR(100) | Discord channel ID |
| channel_type | VARCHAR(50) | Project, Announcement, Research |
| created_at | TIMESTAMPTZ | Creation date |

This table connects Prism Desk projects with their Discord channels.

## 11.3 discord_notification_logs

Records notification delivery attempts.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Recipient |
| event_type | VARCHAR(100) | Notification event |
| delivery_status | VARCHAR(30) | Pending, Sent, Failed |
| attempted_at | TIMESTAMPTZ | Attempt time |
| error_message | TEXT | Failure information |

No Discord message attachments will be copied into PostgreSQL.

---

# 12. Notification Tables

## 12.1 notification_preferences

Stores notification settings for each user.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | User reference |
| event_type | VARCHAR(100) | Notification category |
| is_enabled | BOOLEAN | Enabled or disabled |
| updated_at | TIMESTAMPTZ | Last update |

Each user can independently enable or disable notification categories.

Initial event types:

- Task assignment.
- Task deadline.
- Task submission.
- Handbook comment.
- Handbook reply.
- New research paper.
- New project.
- Project membership change.
- Laboratory announcement.

Notifications are delivered through Discord.

---

# 13. Guest Permission Tables

## 13.1 guest_project_permissions

Stores project-level guest permissions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| guest_user_id | UUID | Guest reference |
| project_id | UUID | Project reference |
| can_view_project | BOOLEAN | Project visibility |
| can_view_research | BOOLEAN | Research access |
| can_view_discussions | BOOLEAN | Discussion access |
| can_participate | BOOLEAN | Participation permission |
| can_create_records | BOOLEAN | Record creation |
| granted_by | UUID | Administrator |
| created_at | TIMESTAMPTZ | Permission date |

## 13.2 guest_feature_permissions

Provides more detailed guest permissions.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| guest_user_id | UUID | Guest reference |
| project_id | UUID | Optional project scope |
| feature_name | VARCHAR(100) | Feature |
| permission_level | VARCHAR(30) | None, View, Create, Edit |
| granted_by | UUID | Administrator |
| created_at | TIMESTAMPTZ | Permission date |

Guest permissions must be explicitly granted by an administrator.

The backend must enforce the effective permission after combining global role restrictions and project-level permissions.

---

# 14. Activity and Audit Tables

## 14.1 activity_logs

Records important application activities.

| Column | Data Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | User who performed action |
| action_type | VARCHAR(100) | Activity type |
| entity_type | VARCHAR(100) | Affected entity |
| entity_id | UUID | Affected record |
| project_id | UUID | Associated project |
| details | JSONB | Relevant change information |
| created_at | TIMESTAMPTZ | Activity timestamp |

Examples:

- Project created.
- Task updated.
- Paper added.
- Handbook edited.
- Member added.
- Member removed.
- Project archived.
- Project deleted.
- Project restored.
- Account approved.

Audit records should be protected from ordinary user modification.

Sensitive values, passwords and session tokens must never be recorded.

---

# 15. Important Database Relationships

The following relationships define the core database structure.

| Parent Entity | Child Entity | Relationship |
|---|---|---|
| Users | User Roles | One-to-many |
| Roles | User Roles | One-to-many |
| Users | Projects | One-to-many as owner |
| Projects | Project Members | One-to-many |
| Users | Project Members | One-to-many |
| Research Papers | Paper Projects | One-to-many |
| Projects | Paper Projects | One-to-many |
| Users | Paper Reading Status | One-to-many |
| Users | Personal Research Notes | One-to-many |
| Projects | Tasks | One-to-many |
| Tasks | Task Assignments | One-to-many |
| Users | Task Assignments | One-to-many |
| Task Assignments | Task Submissions | One-to-many over submission versions |
| Task Submissions | Submission Links | One-to-many |
| Task Submissions | Task Reviews | One-to-many |
| Users | Daily Handbooks | One-to-many |
| Projects | Daily Handbooks | One-to-many |
| Daily Handbooks | Handbook Comments | One-to-many |
| Handbook Comments | Handbook Replies | One-to-many |
| Daily Handbooks | Handbook Edit History | One-to-many |
| Projects | Conferences | One-to-many |
| Users | Discord Accounts | One-to-one initially |
| Projects | Discord Channels | One-to-many |
| Users | Notification Preferences | One-to-many |
| Users | Activity Logs | One-to-many |

---

# 16. Data Integrity and Constraints

The database must enforce important consistency rules.

## 16.1 User Constraints

- Username must be unique.
- Email must be unique.
- User accounts must have valid roles.
- Unapproved accounts cannot access protected resources.

## 16.2 Project Constraints

- Every project must have an owner.
- Project ownership must reference a valid user.
- Duplicate active project memberships are not allowed.
- Deleted projects must have deletion metadata.

## 16.3 Research Paper Constraints

- Paper records should not be duplicated unnecessarily.
- Duplicate paper-project associations are not allowed.
- DOI can be used as a deduplication identifier when available.
- Reading status belongs to an individual user.

## 16.4 Task Constraints

- Official tasks must belong to a project.
- Personal tasks must belong to their creator.
- Duplicate active assignments should be prevented.
- Each student must have an independent assignment record.
- Task submissions must contain text, links or both.

## 16.5 Handbook Constraints

- One project-wise entry per student, project and date.
- One overall summary per student and date.
- Only the student can edit their own entries.
- Historical edits should be preserved.

## 16.6 Conference Constraints

- Every conference record must belong to a project.
- Submission deadlines must be valid timestamps.
- The creator must be a permitted project member or administrator/professor.

---

# 17. Project Deletion and Data Retention

Prism Desk will use safe project deletion.

## 17.1 Soft Deletion

When an administrator deletes a project:

1. The project status changes to Deleted.
2. The deletion timestamp is recorded.
3. The administrator who deleted it is recorded.
4. The recovery expiration date is calculated as 90 days after deletion.
5. Associated project records are retained.
6. The project disappears from normal active project listings.

## 17.2 Restoration

When an administrator restores a project:

- Project status returns to Active.
- Deletion metadata is cleared.
- Project membership is restored.
- Tasks and submissions remain available.
- Research paper associations remain available.
- Handbook records remain available.
- Conference records remain available.

## 17.3 Permanent Deletion

Administrators can permanently delete a project before or after the 90-day retention period.

Permanent deletion should remove project-owned records and project associations.

Shared research paper records must not be deleted if they remain associated with other projects or the laboratory-wide library.

Audit and legally or operationally required administrative records should follow a separate retention policy.

Permanent deletion must require explicit confirmation.

---

# 18. Database Indexing

Indexes should be created for frequently accessed fields.

Recommended indexes:

| Table | Indexed Fields |
|---|---|
| users | username, email, account_status |
| projects | owner_id, status |
| project_members | project_id, user_id |
| research_papers | title, DOI |
| paper_projects | paper_id, project_id |
| tasks | project_id, due_date |
| task_assignments | task_id, student_id, status |
| daily_handbooks | student_id, project_id, entry_date |
| daily_summaries | student_id, summary_date |
| conferences | project_id, submission_deadline |
| activity_logs | user_id, project_id, created_at |

Indexes should be refined based on actual query patterns.

---

# 19. Database Backup

PostgreSQL will be backed up automatically every day.

Initial backup location:

Laboratory workstation.

The backup must include all important application records.

Recommended implementation:

- Automated `pg_dump`.
- Timestamped backup filenames.
- Backup completion logs.
- Backup integrity checks.
- Documented restoration procedure.

The same-workstation backup arrangement is an initial operational choice, not a complete disaster-recovery solution.

An external backup location should be added later.

---

# 20. Storage Policy

Prism Desk will not have an attachment-storage subsystem.

The following data types are permitted:

- Text.
- URLs.
- Metadata.
- Structured records.
- JSON configuration and audit information.

The following are prohibited:

- PDF uploads.
- Word uploads.
- PowerPoint uploads.
- Image uploads.
- Screenshot uploads.
- Video uploads.
- Audio uploads.
- ZIP uploads.
- Dataset uploads.
- Discord attachment downloads.

Discord remains responsible for its own message attachments.

Prism Desk will not maintain copies.

---

# 21. Proposed SQLAlchemy Model Organisation

The backend database models should be organised as follows:

```text
backend/app/models/
|
├── user.py
├── role.py
├── user_session.py
├── project.py
├── project_member.py
├── research_paper.py
├── paper_project.py
├── reading_status.py
├── research_note.py
├── task.py
├── task_assignment.py
├── task_submission.py
├── task_review.py
├── handbook.py
├── handbook_comment.py
├── handbook_history.py
├── conference.py
├── discord_account.py
├── discord_channel.py
├── notification.py
├── guest_permission.py
└── activity_log.py
```

The model definitions should be separated from API schemas and business logic.

---

# 22. Database Design Acceptance Criteria

The database design will be considered ready for implementation when:

1. All major entities have been identified.
2. Primary keys and foreign keys are defined.
3. User-role relationships support multiple roles.
4. Project membership supports multiple projects.
5. Multiple professors can supervise one project.
6. Research papers can be shared across projects.
7. Multi-student task assignments have individual submissions.
8. Handbook entries support project-wise and overall daily records.
9. Handbook comments and replies are supported.
10. Personal research notes remain private.
11. Conference deadlines are associated with projects.
12. Discord accounts can be linked to users.
13. Notification preferences are maintained per user.
14. Guest permissions are configurable.
15. Project soft deletion and restoration are supported.
16. Activity history is maintained.
17. No attachment-storage tables or file-upload fields are introduced.

---

# 23. Final Database Design Statement

Prism Desk will use a relational PostgreSQL database with a modular and normalised structure.

User accounts, projects, project memberships, tasks, research papers, handbooks, conferences, Discord integrations and audit records will be maintained through separate but connected entities.

The design will support multiple roles, multiple project memberships, shared research papers and independent task submissions.

Project-wise research records will remain associated with their projects, while common research resources can be shared across multiple projects.

The database will preserve student ownership of personal research notes and handbook entries.

No file or attachment storage will be implemented.

**Document Status:** Database Design and ER Diagram Specification – Version 1.0.