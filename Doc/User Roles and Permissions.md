# PRISM DESK
## User Roles and Permissions

**Project:** Prism Desk  
**Laboratory:** PRISM Laboratory  
**Document:** User Roles and Permissions Specification  
**Version:** 1.0  
**Phase:** Phase 0 – Requirements Analysis  
**Status:** Initial Permissions Baseline

---

# 1. Introduction

## 1.1 Purpose

This document defines the permissions and responsibilities of users within Prism Desk.

The application supports four roles:

1. Administrator
2. Professor
3. Student
4. Guest

Each role has different access privileges depending on its responsibilities.

The objective is to ensure that users can access the information and functionality necessary for their work without receiving unnecessary permissions.

## 1.2 Access Control Approach

Prism Desk will use Role-Based Access Control (RBAC).

Under this approach:

- Every authenticated user has an assigned role.
- Each role has predefined permissions.
- Access to projects and their records depends on project membership.
- Guest permissions are configurable by administrators.
- Sensitive operations require appropriate authorisation.

The backend must enforce permissions. Hiding a button in the frontend is not sufficient security.

---

# 2. Role Definitions

## 2.1 Administrator

The Administrator has system-level management privileges.

Initially, both designated laboratory administrators will have administrator privileges.

### Responsibilities

- Manage user accounts.
- Approve or reject registrations.
- Assign user roles.
- Create and manage projects.
- Add and remove project members.
- Manage guest permissions.
- Manage archived and deleted projects.
- Monitor laboratory activities.
- View system dashboards.
- Manage administrative settings.
- Monitor database and application health.

### Administrator Permissions

| Function | Permission |
|---|---|
| View laboratory dashboard | Full |
| View user list | Yes |
| Approve registrations | Yes |
| Reject registrations | Yes |
| Create users | Yes |
| Edit user accounts | Yes |
| Deactivate accounts | Yes |
| Assign roles | Yes |
| Create projects | Yes |
| Edit projects | Yes |
| Archive projects | Yes |
| Delete projects | Yes |
| Restore deleted projects | Yes |
| Permanently delete projects | Yes |
| Add project members | Yes |
| Remove project members | Yes |
| Manage guest permissions | Yes |
| View laboratory research library | Yes |
| Manage research resources | Yes |
| View project tasks | According to authorised access |
| Manage official tasks | Yes |
| View handbook records | According to authorised access |
| Modify student handbook entries | No |
| Comment on handbooks | No, unless separately assigned professor privileges |
| View students' private research notes | No |
| Manage Discord integration | Yes |
| View activity history | Yes |
| Manage notification settings | System-level |

**Important:** Administrator privileges do not automatically provide access to students' private research notes.

## 2.2 Professor

Professors are responsible for research supervision and project management.

A professor may supervise multiple projects and multiple students.

Multiple professors can supervise the same project.

### Responsibilities

- Create research projects.
- Supervise project members.
- Add and remove project members.
- Assign official research tasks.
- Review task submissions.
- Provide feedback.
- Monitor student research progress.
- Comment on daily handbook entries.
- Recommend research papers.
- Monitor reading status.
- Add conference deadlines.
- Monitor project progress.

### Professor Permissions

| Function | Permission |
|---|---|
| View professor dashboard | Yes |
| View supervised projects | Yes |
| Create projects | Yes |
| Edit supervised projects | Yes |
| Archive projects | Subject to project permissions |
| Permanently delete projects | No |
| Add project members | Yes |
| Remove project members | Yes |
| Create official tasks | Yes |
| Assign tasks to students | Yes |
| Assign one task to multiple students | Yes |
| Review task submissions | Yes |
| Request task revisions | Yes |
| Mark tasks completed | Yes |
| Create personal student tasks | No |
| View project research library | Yes |
| Add research papers | Yes |
| Recommend research papers | Yes |
| View student reading status | Yes |
| View student personal research notes | No |
| View student handbook entries | Yes, within authorised supervision scope |
| Edit student handbook entries | No |
| Delete student handbook entries | No |
| Comment on handbook entries | Yes |
| Reply to student handbook comments | Yes |
| Add conference deadlines | Yes |
| View project discussions | Yes, according to channel access |
| Manage Discord integration | According to administrator permissions |
| View activity history | Within authorised project scope |

## 2.3 Student

Students are the primary research contributors within Prism Desk.

A student can participate in multiple research projects simultaneously.

Students can also create their own research projects.

### Responsibilities

- Maintain daily research handbooks.
- Complete assigned tasks.
- Create personal research tasks.
- Add research papers.
- Maintain paper reading status.
- Maintain private research notes.
- Submit research progress.
- Participate in project discussions.
- Reply to professor feedback.
- Track conference deadlines.

### Student Permissions

| Function | Permission |
|---|---|
| View student dashboard | Yes |
| Register an account | Yes |
| Create projects | Yes |
| Edit own project details | According to project ownership permissions |
| Add project members | No |
| Remove project members | No |
| Join multiple projects | Yes, through authorised membership |
| View project information | As a project member |
| View project tasks | Yes |
| Create official project tasks | No |
| Create personal tasks | Yes |
| Update personal task status | Yes |
| View assigned tasks | Yes |
| Submit task responses | Yes |
| Edit own submissions | According to task review status and workflow rules |
| View other students' private submissions | No |
| View project research papers | Yes |
| Add research papers | Yes |
| Update own reading status | Yes |
| Maintain personal research notes | Yes |
| View other students' personal notes | No |
| View own handbook | Yes |
| Create project-wise handbook entries | Yes |
| Create overall daily summaries | Yes |
| Edit own handbook entries | Yes |
| Delete own draft entries | Yes |
| Comment on handbook entries | No |
| Reply to professor comments | Yes |
| Add conference deadlines | Yes, if a member of the associated project |
| View conference deadlines | According to project membership |
| Access Discord channels | According to project membership |
| View laboratory announcements | Yes |
| View administrative activity logs | No |

### Student Project Creation

When a student creates a project:

1. The project becomes active immediately.
2. The student automatically becomes its project owner.
3. The project becomes visible to administrators and professors.
4. The student cannot independently add or remove project members.
5. Administrators and professors can manage its membership.

## 2.4 Guest

Guests are users who require limited access to selected laboratory information.

Guest permissions will be customised by administrators.

There will be no automatic assumption that a guest can access all laboratory projects or research records.

### Guest Permission Configuration

Administrators should be able to configure:

| Permission | Configurable |
|---|---|
| View selected projects | Yes |
| View project descriptions | Yes |
| View selected research papers | Yes |
| View research resources | Yes |
| View conference deadlines | Yes |
| View project discussions | Yes |
| Participate in discussions | Yes |
| Add research papers | Yes |
| Create projects | Yes |
| Create tasks | Yes |
| View student handbooks | Yes |
| View task submissions | Yes |
| Edit records | Yes, if explicitly authorised |
| Manage project members | Yes, if explicitly authorised |
| Access laboratory-wide dashboard | Yes, if explicitly authorised |

Guest permissions should follow the principle of least privilege.

By default, guests should receive read-only access to explicitly selected resources.

Any additional permission must be granted by an administrator.

---

# 3. Project-Level Access Control

Project membership determines access to project-specific information.

## 3.1 Project Creation

The following roles can create research projects:

- Administrator
- Professor
- Student

New projects become active immediately.

The creator automatically becomes the project owner.

Guest project creation is disabled by default and may be enabled through explicit administrator permission.

## 3.2 Project Membership Management

Only administrators and professors can add or remove project members.

Students cannot independently manage project membership, even if they created the project.

## 3.3 Multiple Project Membership

The system must support:

- One student participating in multiple projects.
- One professor supervising multiple projects.
- Multiple professors supervising one project.
- Multiple students belonging to one project.

## 3.4 Project Data Isolation

Each project maintains its own:

- Members.
- Tasks.
- Task assignments.
- Task submissions.
- Handbook entries.
- Project discussions and associated records.
- Conference deadlines.

Project members can access records associated with their projects according to their roles.

---

# 4. Research Library Permissions

Prism Desk will maintain:

1. Laboratory-wide Research Library.
2. Project-wise Research Libraries.

## 4.1 Research Paper Permissions

| Action | Administrator | Professor | Student | Guest |
|---|---|---|---|---|
| View laboratory papers | Yes | Yes | Yes | Configurable |
| Add papers | Yes | Yes | Yes | Configurable |
| View project papers | Yes | Yes | Project members | Configurable |
| Associate papers with projects | Yes | Yes | Yes | Configurable |
| View reading status | Yes | Yes | Own status | No by default |
| Update own reading status | No by default | No by default | Yes | Configurable |
| Maintain personal notes | No by default | No by default | Yes | Configurable |
| View student personal notes | No | No | Own notes only | No |

## 4.2 Personal Research Notes

Personal research notes must remain private to their owners.

Neither administrators nor professors should have access to these notes by default.

The system must enforce this restriction through backend authorisation.

---

# 5. Task Management Permissions

Prism Desk supports official project tasks and personal research tasks.

## 5.1 Official Project Tasks

Official tasks can be created by administrators and professors.

| Action | Administrator | Professor | Student | Guest |
|---|---|---|---|---|
| Create official tasks | Yes | Yes | No | Configurable |
| Assign tasks | Yes | Yes | No | Configurable |
| Assign to multiple students | Yes | Yes | No | Configurable |
| View assigned tasks | Yes | Yes | Own assignments | Configurable |
| Submit work | No | No | Yes | Configurable |
| Review submissions | Yes | Yes | No | Configurable |
| Request revisions | Yes | Yes | No | Configurable |
| Mark completed | Yes | Yes | No | Configurable |

Each student assigned to a shared task must have an independent submission record.

## 5.2 Personal Tasks

Students can create personal research tasks for their own work tracking.

Personal tasks are separate from official professor-assigned tasks.

They do not require professor approval.

---

# 6. Daily Research Handbook Permissions

Each student maintains:

1. One entry per project per day.
2. One overall daily summary.

## 6.1 Handbook Permissions

| Action | Administrator | Professor | Student |
|---|---|---|---|
| View student entries | According to authorised access | Yes, within supervision scope | Own entries |
| Create handbook entries | No | No | Yes |
| Edit handbook entries | No | No | Yes |
| Delete own draft entries | No | No | Yes |
| Comment on entries | No by default | Yes | No |
| Reply to professor comments | No | No | Yes |
| Modify student entries | No | No | Yes |
| View edit history | Authorised audit access | According to supervision scope | Own history |

## 6.2 Handbook Editing

Students retain editing control over their own handbook entries, including after submission.

Professors can provide comments but cannot edit or delete student entries.

## 6.3 Handbook Audit History

The system should maintain a history of handbook edits.

This history should record:

- Entry identifier.
- User who made the change.
- Date and time.
- Type of change.

The history should help preserve accountability without preventing students from updating their research diaries.

---

# 7. Conference and Deadline Permissions

Any member of a project can add conference and Call for Papers deadline information.

| Action | Administrator | Professor | Student | Guest |
|---|---|---|---|---|
| View conference deadlines | Yes | Yes | Project members | Configurable |
| Add conference deadlines | Yes | Yes | Yes, as project member | Configurable |
| Edit conference records | Yes | Yes | Subject to project permissions | Configurable |
| Delete conference records | Yes | Yes, subject to project permissions | Subject to project permissions | Configurable |
| Receive deadline notifications | Yes | Yes | Yes | Configurable |

Conference records should contain the conference name, official website, CFP link, submission deadline and associated project.

---

# 8. Discord Permissions

Discord will be the primary communication platform.

Prism Desk will integrate with the laboratory Discord server.

## 8.1 Account Linking

Users should be able to associate their Prism Desk account with their individual Discord account.

The system should maintain a secure mapping between the two accounts.

## 8.2 Discord Access

Project Discord channels should follow project membership and Discord server permissions.

Users should not receive access to private project channels simply because they have a Prism Desk account.

## 8.3 Attachment Policy

Discord may be used to share screenshots and other attachments.

Prism Desk must not download or store these attachments.

---

# 9. Notification Permissions

Notifications will be delivered through Discord.

The following events should generate notifications by default:

- New task assignments.
- Approaching task deadlines.
- Task submissions.
- Professor handbook comments.
- Student replies.
- New research papers.
- New projects.
- Project membership changes.
- Laboratory announcements.

Each user can disable individual notification event types.

Notification preferences must be stored separately for each user.

---

# 10. Administrator Approval and Account Management

Newly registered users cannot access protected application functionality until an administrator approves their accounts.

## 10.1 Registration Workflow

```text
User Registration
       |
       v
Pending Approval
       |
       v
Administrator Review
       |
       +------> Rejected
       |
       v
Approved
       |
       v
Role Assignment
       |
       v
Prism Desk Access
```

## 10.2 Account Management

Administrators can:

- Approve registrations.
- Reject registrations.
- Change user roles.
- Deactivate accounts.
- Reactivate accounts.
- Manage guest access.

Role changes must be recorded in the audit history.

---

# 11. Project Lifecycle Permissions

| Operation | Administrator | Professor | Student |
|---|---|---|---|
| Create project | Yes | Yes | Yes |
| Become project owner | If creator | If creator | If creator |
| Edit project | Yes | Subject to project permissions | Subject to ownership permissions |
| Add members | Yes | Yes | No |
| Remove members | Yes | Yes | No |
| Archive project | Yes | Subject to project permissions | Subject to project permissions |
| View archived projects | Yes | Authorised access | Authorised access |
| Delete project | Yes | No | No |
| Restore deleted project | Yes | No | No |
| Permanently delete project | Yes | No | No |

Deleted projects remain recoverable for 90 days unless an administrator permanently deletes them earlier.

---

# 12. Activity History and Audit Permissions

The application must record important activities.

Examples include:

- User registration and approval.
- Role changes.
- Project creation.
- Project updates.
- Project membership changes.
- Task creation and status updates.
- Research paper additions.
- Handbook creation and edits.
- Project archiving.
- Project deletion and restoration.

Administrators can view laboratory-wide audit records.

Professors can view relevant project activity.

Students can view their own relevant activity.

Audit records must not expose private research notes.

---

# 13. Permission Enforcement Requirements

The backend must enforce all permissions.

The following rules are mandatory:

1. A user cannot access a project merely by knowing its project ID.
2. A student cannot add or remove project members.
3. A professor cannot modify student handbook entries.
4. A professor cannot view private student research notes.
5. An administrator cannot view private student research notes by default.
6. A student cannot review another student's private task submission.
7. A guest cannot access resources outside the permissions granted by an administrator.
8. An unapproved account cannot access protected application resources.
9. Only administrators can permanently delete projects.
10. Deleted project records must not remain accessible through ordinary project routes.
11. Discord account linking must be validated before private information is sent to Discord.
12. Notification preferences must be respected for each user.

---

# 14. Future Permission Extensions

The permission system should be designed so that additional roles and permissions can be introduced without redesigning the entire application.

Possible future roles include:

- Research Assistant.
- Lab Coordinator.
- External Collaborator.
- Visiting Researcher.

These roles are not part of the initial four-role baseline.

---

# 15. Final Permission Policy

Prism Desk will use four primary roles with role-based permissions and project-level access restrictions.

Administrators manage the overall application.

Professors supervise research activities and manage project membership.

Students create research records, complete tasks and maintain their daily handbooks.

Guests receive only the permissions explicitly assigned by administrators.

The system must preserve student ownership of personal research notes and handbook entries while allowing professors to provide research supervision and feedback.

**Document Status:** User Roles and Permissions Specification – Version 1.0.