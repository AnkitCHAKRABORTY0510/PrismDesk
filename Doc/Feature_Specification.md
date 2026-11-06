# PRISM DESK
## Feature Specification
**Document:** 6 of Phase 0 — Requirements Analysis and System Design  
**Version:** 1.0  
**Application:** Prism Desk  
**Tagline:** One Lab. Multiple Projects. Connected Research.

---

# 1. Introduction

## 1.1 Purpose

This document defines the functional features of Prism Desk in sufficient detail to guide implementation.

It specifies:
- Application screens and modules.
- Features available to each user role.
- User actions and system responses.
- Data validation and permission rules.
- Search, filtering, and sorting requirements.
- Error handling and acceptance criteria.

## 1.2 Application Overview

Prism Desk is a browser-based laboratory management and research collaboration application.

It will provide a central platform for managing:
- Laboratory users and permissions.
- Research projects.
- Research papers and reading progress.
- Tasks and submissions.
- Daily research handbooks.
- Conference deadlines.
- Notifications through Discord.
- Laboratory activity and audit records.

The application will use PostgreSQL as its central data store.

**Important restrictions:**
1. Prism Desk will not provide internal chat.
2. Discord will be the only communication platform.
3. Prism Desk will not support file uploads or attachment storage.
4. Research papers will be stored as metadata and external links, not uploaded PDFs.
5. Discord attachments will remain within Discord and must never be downloaded or stored by Prism Desk.

---

# 2. User Authentication and Account Management

## 2.1 Registration Screen

### Required fields
- Full name
- Username
- Email address
- Password
- Confirm password

### User actions
- Register an account.
- Navigate to the login screen.

### System behaviour
1. Validate all required fields.
2. Check username uniqueness.
3. Check email uniqueness.
4. Validate password requirements.
5. Confirm that both password fields match.
6. Create the account with Pending Approval status.
7. Display a registration confirmation message.
8. Notify administrators about the pending registration through the configured Discord notification system.

### Validation rules
- Username must be unique.
- Email must be unique and valid.
- Password must meet the configured password policy.
- Password and confirmation must match.
- Empty required fields must be rejected.

A pending account must not gain access to protected application features.

## 2.2 Login Screen

### Login fields
- Username or email
- Password

### Features
- Login.
- Password reset.
- Display appropriate authentication errors.

### System behaviour
- Authenticate the supplied credentials.
- Check account approval status.
- Check whether the account is active.
- Establish a secure server-managed session.
- Redirect the user to the appropriate dashboard.

### Possible login states
| Condition | System response |
|---|---|
| Valid credentials and approved account | Login successful |
| Incorrect credentials | Display authentication error |
| Pending approval | Inform user that approval is pending |
| Rejected account | Deny access |
| Deactivated account | Deny access |
| Expired session | Require login again |

## 2.3 Password Reset

Features:
- Request password reset.
- Verify reset request using a secure verification mechanism.
- Set a new password.
- Invalidate previously active sessions where appropriate.

Password reset tokens must be securely generated, time-limited, and single-use.

## 2.4 Session Management

Features:
- Automatic logout after inactivity.
- Secure session creation and invalidation.
- Logout from the current session.
- Protection against unauthorised session access.

---

# 3. User and Role Management

## 3.1 User Management Screen

Available to administrators.

### Display information
- Full name
- Username
- Email
- Assigned roles
- Account status
- Registration date
- Last login

### Administrator actions
- Approve registration.
- Reject registration.
- Assign roles.
- Modify roles.
- Deactivate account.
- Reactivate account.
- View relevant account activity.

## 3.2 Role Management

The application must support four roles:

1. Administrator
2. Professor
3. Student
4. Guest

A user account must support multiple roles. For example, an administrator may also have professor privileges.

### Guest permissions

Guest access must be configurable by an administrator.

Permissions can be assigned:
- Per project.
- Per application feature.
- As read-only or another explicitly granted permission.

Guest access must be denied by default until permissions are assigned.

## 3.3 Registration Approval Screen

The administrator dashboard must include a registration queue.

Features:
- View pending registrations.
- Review account information.
- Approve registration.
- Reject registration.

The system must record the administrator's action in the audit history.

---

# 4. Dashboard Module

The application must provide role-based dashboards.

## 4.1 Administrator Dashboard

### Information displayed
- Total users.
- Total professors.
- Total students.
- Total guests.
- Pending registrations.
- Active projects.
- Archived projects.
- Deleted projects.
- Total tasks.
- Pending task reviews.
- Research paper statistics.
- Student activity overview.
- Upcoming conference deadlines.
- Recent audit activities.
- Database and application health indicators.

### Quick actions
- Approve registrations.
- Manage users.
- Create projects.
- View all projects.
- Review laboratory activity.

## 4.2 Professor Dashboard

### Information displayed
- Supervised projects.
- Project members.
- Assigned tasks.
- Pending submissions.
- Tasks requiring review.
- Tasks requiring revision.
- Student handbook entries.
- Student research reading activity.
- Upcoming deadlines.
- Conference deadlines.
- Recent project activity.

### Quick actions
- Create project.
- Create official task.
- Assign tasks.
- Review submissions.
- Comment on handbook entries.
- Add research papers.
- Add conference deadlines.

## 4.3 Student Dashboard

### Information displayed
- My projects.
- Assigned tasks.
- Personal tasks.
- Upcoming deadlines.
- Daily handbook.
- Overall daily summary.
- Research papers.
- Reading progress.
- Professor feedback.
- Conference deadlines.
- Personal research progress.

### Quick actions
- Create project.
- Create personal task.
- Update task progress.
- Submit task.
- Add research paper.
- Update reading status.
- Write daily handbook entry.
- Write overall daily summary.

## 4.4 Guest Dashboard

The guest dashboard must display only the projects and features explicitly permitted by an administrator.

Unauthorised modules must not be accessible through direct URLs or API requests.

---

# 5. Project Management Module

## 5.1 Project Listing Screen

Display projects accessible to the logged-in user.

### Project information
- Project name.
- Project description.
- Project owner.
- Supervising professors.
- Project members.
- Creation date.
- Project status.

### Available filters
- Active projects.
- Archived projects.
- Projects owned by the user.
- Projects supervised by the user.
- Projects in which the user is a member.

## 5.2 Create Project Screen

Available to administrators, professors, and students.

### Required information
- Project name.
- Project description.
- Research area.
- Project objectives.
- Creation date.

### System behaviour
1. Validate the project information.
2. Create the project.
3. Set the creator as project owner.
4. Add the creator as a project member.
5. Set the project status to Active.
6. Make the project available immediately.

Student-created projects do not require approval.

## 5.3 Project Details Screen

Each project must have a dedicated workspace.

### Project sections
- Overview.
- Members.
- Research Library.
- Tasks.
- Daily Handbook.
- Conference Tracker.
- Activity History.

Only authorised sections should be visible to the user.

## 5.4 Project Membership Management

Available to administrators and professors.

Features:
- Add students.
- Add professors.
- Remove project members.
- View project membership.

Rules:
- Multiple professors can supervise one project.
- One professor can supervise multiple projects.
- Students can participate in multiple projects.
- Student project owners cannot add or remove members.

## 5.5 Project Lifecycle

Project statuses:

| Status | Description |
|---|---|
| Active | Project is currently running |
| Archived | Project is inactive but retained |
| Deleted | Project is in the recoverable Deleted Items area |

### Archive
- Preserve all project records.
- Remove the project from active project views.
- Retain access for authorised users according to the final archive permissions.

### Delete
- Move the project to Deleted Items.
- Start a 90-day recovery period.
- Preserve shared research papers and records linked to other projects.
- Do not immediately destroy related data.

### Restore
- Only administrators can restore deleted projects.
- Restore the project and its retained records.

### Permanent deletion
- Only administrators can permanently delete projects.
- Permanent deletion must require an explicit confirmation.
- Related shared research papers must not be deleted if they are still used elsewhere.

---

# 6. Research Library Module

## 6.1 Library Structure

The Research Library must contain two collections:

1. Laboratory-wide Research Library.
2. Project-wise Research Collections.

A research paper must be stored once and linked to multiple projects when necessary.

## 6.2 Add Research Paper Screen

Available to students and professors.

### Paper metadata
- Paper title.
- Authors.
- Publication year.
- Journal or conference.
- DOI.
- External URL.
- Abstract.
- Research area.
- Keywords.
- Collection type.
- Associated project or projects.

### System behaviour
1. Validate the title and metadata.
2. Check for duplicate records using DOI or other available identifying information.
3. Create or reuse the research paper record.
4. Associate the paper with the selected projects.
5. Record who added the paper.
6. Notify relevant users through Discord according to their notification preferences.

**File restriction:** Users cannot upload PDFs or other paper files. They may provide an external paper URL or DOI.

## 6.3 Research Paper Details Screen

Display:
- Paper title.
- Authors.
- Publication details.
- Abstract.
- DOI.
- External link.
- Research area.
- Added by.
- Associated projects.

## 6.4 Reading Status

Students can maintain individual reading progress.

Statuses:

| Status | Meaning |
|---|---|
| Not Started | Paper has not been read |
| Reading | Currently reading |
| Completed | Reading completed |

Reading status must be associated with the individual student and paper.

## 6.5 Personal Research Notes

Students can create private notes associated with research papers.

Features:
- Add notes.
- Edit notes.
- View personal notes.
- Delete personal notes.

Privacy rules:
- Professors cannot view student personal research notes.
- Administrators cannot view student personal research notes by default.
- Notes must not appear in audit logs or public project activity.

---

# 7. Task Management Module

## 7.1 Task Types

Two task types must be supported:

1. Official Tasks.
2. Personal Tasks.

Official tasks are created by administrators and professors.

Personal tasks are created by students for their own research tracking.

## 7.2 Create Official Task Screen

Available to administrators and professors.

### Required fields
- Task title.
- Task description.
- Associated project.
- Assigned student or students.
- Start date.
- Deadline.
- Priority.
- Optional instructions.

### System behaviour
1. Validate task details.
2. Create the task.
3. Create a separate assignment record for each assigned student.
4. Notify assigned students through Discord.
5. Display the task in their dashboards.

When one task is assigned to multiple students, each student must have an independent assignment and submission record.

## 7.3 Create Personal Task Screen

Available to students.

Fields:
- Task title.
- Description.
- Project association, if applicable.
- Deadline.
- Priority.

Personal tasks do not require professor assignment.

## 7.4 Task Listing Screen

Display:
- Task title.
- Task type.
- Project.
- Assigned student.
- Deadline.
- Priority.
- Current status.

### Filters
- To Do.
- In Progress.
- Under Review.
- Revision Required.
- Completed.
- Overdue.
- Project.
- Priority.
- Assigned student, where authorised.

## 7.5 Task Workflow

The official task workflow is:

**To Do → In Progress → Under Review → Revision Required → Under Review → Completed**

### Status descriptions

| Status | Description |
|---|---|
| To Do | Task has not started |
| In Progress | Student is working on the task |
| Under Review | Student has submitted work |
| Revision Required | Professor has requested changes |
| Completed | Professor has accepted the submission |

The system must allow repeated submission and review cycles.

## 7.6 Task Submission Screen

Students can submit:
- Written text.
- External links.

The application must not provide file upload or attachment functionality.

### Submission behaviour
1. Student enters submission text or external links.
2. System validates the submission.
3. System creates a submission record.
4. Assignment status changes to Under Review.
5. Professor receives a Discord notification.

Each submission must be stored as a version so previous submissions remain available for review.

## 7.7 Task Review Screen

Available to the assigned professor or authorised administrator.

Features:
- View submitted text.
- Open external links.
- Add feedback.
- Request revision.
- Mark task as completed.

Students must not be able to view other students' private submissions.

---

# 8. Daily Research Handbook Module

## 8.1 Handbook Structure

Each student maintains:

1. One project-wise daily entry for every active project in which they participate.
2. One separate overall daily summary.

The system must enforce one entry per student, project, and date, and one overall summary per student and date.

## 8.2 Project-wise Daily Entry

### Fields
- Date.
- Project.
- Work completed.
- Research progress.
- Problems encountered.
- Next steps.

### Student actions
- Create entry.
- Edit entry.
- Submit entry.
- Edit previously submitted entry.

Students may edit entries even after professor comments.

## 8.3 Overall Daily Summary

The overall summary records the student's work across projects and other research activities.

Features:
- Create summary.
- Edit summary.
- View previous summaries.

It must remain separate from project-specific handbook entries.

## 8.4 Professor Comments

Professors can:
- View authorised students' project-wise entries.
- Add comments.
- View student replies.

Professors cannot:
- Edit student entries.
- Delete student entries.

Students can:
- View professor comments.
- Reply to comments.
- Continue editing their entries.

## 8.5 Handbook Edit History

Every edit must create an edit-history record containing:
- Student identifier.
- Handbook entry identifier.
- Previous content.
- Updated content.
- Edit timestamp.

The history must be available for authorised review.

---

# 9. Conference and Deadline Tracker

## 9.1 Conference Listing Screen

Display:
- Conference name.
- Official website.
- Call for Papers URL.
- Submission deadline.
- Associated project.
- Added by.
- Remaining time.

## 9.2 Add Conference Screen

Any member of a project team can add a conference deadline.

### Fields
- Conference name.
- Official website.
- CFP URL.
- Submission deadline.
- Associated project.
- Reminder configuration.

### System behaviour
1. Validate conference information.
2. Validate the deadline.
3. Store the conference record.
4. Associate it with the selected project.
5. Display the deadline on relevant dashboards.
6. Schedule Discord reminders according to the configured reminder policy.

## 9.3 Deadline Display

Display:
- Upcoming deadlines.
- Remaining days.
- Deadline date and time.
- Associated project.

The system must use timezone-aware date and time handling.

The default laboratory timezone should be configurable. The initial deployment may use Asia/Kolkata.

---

# 10. Discord Integration Module

## 10.1 Integration Overview

Discord is the only communication and notification platform.

Prism Desk will not implement:
- Internal chat.
- Direct messaging.
- Internal discussion threads.
- File sharing or attachment hosting.

## 10.2 Discord Account Linking

Each user can link an individual Discord account.

The linking process must use a secure verification mechanism, preferably Discord OAuth2.

The system must maintain a secure mapping between:
- Prism Desk user.
- Discord user ID.

## 10.3 Laboratory Discord Server

The integration should support configured laboratory channels, such as:
- General.
- Announcements.
- Research.
- Project-specific channels.

Channel access must be managed through Discord permissions and the integration configuration.

## 10.4 Notification Events

The following events must be supported:

| Event | Notification |
|---|---|
| New task assignment | Assigned student |
| Approaching task deadline | Assigned student |
| Task submission | Relevant professor |
| Professor handbook comment | Student |
| Student handbook reply | Relevant professor |
| New research paper | Relevant project members |
| New project | Relevant users |
| Project member addition/removal | Affected members |
| Laboratory announcement | Relevant users |
| Conference deadline reminder | Relevant project members |

## 10.5 Notification Preferences

Each user can independently enable or disable supported notification types.

Notifications should be enabled by default.

## 10.6 Notification Failure Handling

If Discord is unavailable:
- Core application functions must continue.
- Database records must still be saved.
- Failed notification attempts must be logged.
- The system must retry failed notifications according to a configured retry policy.

A notification failure must never cause a task, paper, handbook entry, or project operation to fail.

## 10.7 Attachment Handling

Users may share files directly through Discord.

Prism Desk must not:
- Download Discord attachments.
- Copy attachments into its database.
- Store attachment URLs as a substitute for application file storage.
- Proxy or mirror Discord files.

Only relevant notification metadata and delivery status should be stored.

---

# 11. Activity and Audit History

## 11.1 Audit Events

The system must record important operations, including:

- Account approval and rejection.
- Role changes.
- Account activation and deactivation.
- Project creation and modification.
- Project archive, deletion, restoration, and permanent deletion.
- Project membership changes.
- Task creation and status changes.
- Task submissions and reviews.
- Research paper additions and updates.
- Handbook creation and editing.
- Conference additions and updates.
- Administrative actions.

## 11.2 Audit Information

Each audit record should contain:
- User identifier.
- Action type.
- Affected record type.
- Affected record identifier.
- Timestamp.
- Relevant non-sensitive change metadata.

## 11.3 Audit Visibility

| Role | Visibility |
|---|---|
| Administrator | Laboratory-wide audit history |
| Professor | Relevant authorised project activity |
| Student | Own relevant activity |
| Guest | No audit access unless explicitly granted |

Private research notes and passwords must never be recorded in audit history.

---

# 12. Search, Filtering, and Sorting

Search should be available across the main application modules.

## 12.1 Project Search
Search by:
- Project name.
- Research area.
- Project owner.
- Project status.

## 12.2 Research Library Search
Search by:
- Paper title.
- Author.
- DOI.
- Publication year.
- Journal or conference.
- Research area.
- Keywords.

## 12.3 Task Search
Search by:
- Task title.
- Project.
- Status.
- Assigned student.
- Deadline.

## 12.4 Handbook Search
Search by:
- Date.
- Project.
- Student, where authorised.

## 12.5 Conference Search
Search by:
- Conference name.
- Project.
- Submission deadline.

All search results must respect the user's access permissions.

---

# 13. Application Navigation and Screen Structure

The main application layout should include:

### Global navigation
- Dashboard.
- Projects.
- Research Library.
- Tasks.
- Daily Handbook.
- Conferences.
- Notifications and Discord settings.
- Profile and Account Settings.

### Administrator-only navigation
- User Management.
- Registration Approvals.
- Deleted Items.
- Audit History.
- System Status.
- Administration Settings.

### Project workspace navigation
- Overview.
- Members.
- Research.
- Tasks.
- Handbook.
- Conferences.
- Activity.

Navigation elements must be dynamically displayed according to the user's permissions.

---

# 14. Validation and Error Handling

The application must provide understandable validation messages.

Examples:

| Situation | Expected response |
|---|---|
| Duplicate username | Username already exists |
| Duplicate email | Email already registered |
| Invalid login | Invalid username/email or password |
| Pending registration | Account awaiting administrator approval |
| Missing project name | Project name is required |
| Invalid deadline | Enter a valid deadline |
| Unauthorised project access | Access denied |
| Duplicate daily entry | An entry already exists for this date |
| Empty task submission | Submission content is required |
| Discord delivery failure | Record saved; notification delivery failed and will be retried |
| Expired session | Session expired; please log in again |

The backend must independently validate all critical inputs and permissions. Frontend validation alone is insufficient.

---

# 15. Security and Permission Enforcement

The following rules are mandatory:

1. Every protected API endpoint must verify authentication.
2. Every protected operation must verify role and resource-level permissions.
3. Users must not access projects merely by changing a project ID in a URL.
4. Students must not access other students' private task submissions.
5. Professors must not access personal research notes.
6. Administrators must not access personal research notes by default.
7. Guest access must be explicitly granted.
8. Session cookies must use appropriate security attributes.
9. Passwords must be securely hashed.
10. Sensitive Discord credentials and tokens must be protected.
11. Database access must be restricted to authorised application services.
12. Audit records must not contain passwords, secrets, or private research notes.

---

# 16. Feature Acceptance Criteria

The application will be considered functionally ready for initial testing when the following conditions are met.

| ID | Acceptance criterion |
|---|---|
| F-01 | Users can register and wait for administrator approval |
| F-02 | Approved users can log in using username or email |
| F-03 | Administrators can assign multiple roles |
| F-04 | Users can access only authorised modules |
| F-05 | Students, professors, and administrators can create projects |
| F-06 | Project creators automatically become project owners and members |
| F-07 | Only administrators and professors can manage project membership |
| F-08 | Projects support Active, Archived, and Deleted states |
| F-09 | Deleted projects can be recovered within 90 days |
| F-10 | Research papers can be shared across multiple projects without duplication |
| F-11 | Students can maintain individual reading statuses |
| F-12 | Personal research notes remain private |
| F-13 | Professors and administrators can create official tasks |
| F-14 | Students can create personal tasks |
| F-15 | Multiple students can receive independent assignments for one task |
| F-16 | Students can submit text and external links only |
| F-17 | Task submissions support revision and resubmission |
| F-18 | Students can create project-wise daily handbook entries |
| F-19 | Students can create separate overall daily summaries |
| F-20 | Professors can comment but cannot edit student handbook entries |
| F-21 | Handbook edit history is maintained |
| F-22 | Project members can add conference deadlines |
| F-23 | Conference deadlines appear on relevant dashboards |
| F-24 | Discord accounts can be securely linked |
| F-25 | Discord notifications respect individual preferences |
| F-26 | Discord failure does not interrupt core application operations |
| F-27 | Important activities are recorded in audit history |
| F-28 | Search results respect user permissions |
| F-29 | No file-upload or attachment-storage functionality exists |
| F-30 | The application works through a browser over the laboratory LAN |

---

# 17. Implementation Priority

The following implementation order is recommended.

## Priority 1 — Core Foundation
- Database connection.
- Authentication.
- Registration approval.
- Role and permission management.
- Application navigation.
- Role-based dashboards.

## Priority 2 — Project Management
- Project creation.
- Project listing.
- Project details.
- Membership management.
- Project lifecycle.

## Priority 3 — Research and Task Management
- Research Library.
- Reading status.
- Personal research notes.
- Official tasks.
- Personal tasks.
- Task assignments.
- Submissions and reviews.

## Priority 4 — Daily Research Management
- Project-wise handbook.
- Overall daily summary.
- Professor comments.
- Student replies.
- Edit history.

## Priority 5 — Collaboration and Deadlines
- Conference Tracker.
- Discord account linking.
- Discord notifications.
- Notification preferences.
- Notification retry handling.

## Priority 6 — Administration and Quality
- Audit history.
- Deleted Items.
- Advanced search and filtering.
- System health information.
- Security testing.
- Integration testing.

---

# 18. Final Specification Statement

This Feature Specification defines the functional implementation requirements for Prism Desk.

The development team should use this document together with:

1. Software Requirements Specification.
2. User Roles and Permissions.
3. System Architecture.
4. Database Design and ER Diagram.
5. User Workflows and Process Specification.

Any implementation decision that changes an approved requirement must be documented and reviewed before development.

The application must maintain three fundamental principles:

- PostgreSQL is the source of truth for laboratory research records.
- Discord is the only communication and notification platform.
- Prism Desk does not upload, download, or store user files or attachments.