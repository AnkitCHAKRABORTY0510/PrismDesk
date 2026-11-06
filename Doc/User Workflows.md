# PRISM DESK
## User Workflows and Process Specification

**Project:** Prism Desk  
**Laboratory:** PRISM Laboratory  
**Document:** User Workflows Specification  
**Version:** 1.0  
**Phase:** Phase 0 – Requirements Analysis and System Design  
**Status:** Initial Workflow Baseline

---

# 1. Introduction

## 1.1 Purpose

This document describes the operational workflows of Prism Desk.

It explains how administrators, professors, students and guests will interact with the application.

The document covers:

1. User registration and approval.
2. Authentication and login.
3. User and role management.
4. Project creation and management.
5. Project membership.
6. Research paper management.
7. Task assignment and submission.
8. Daily research handbook.
9. Professor feedback.
10. Conference and deadline tracking.
11. Discord integration.
12. Notifications.
13. Dashboards.
14. Project archiving and deletion.
15. Guest access.
16. Activity history.

## 1.2 Primary User Roles

Prism Desk supports four roles:

- Administrator
- Professor
- Student
- Guest

All workflows must respect the permissions defined in `USER_ROLES_AND_PERMISSIONS.md`.

---

# 2. User Registration and Approval Workflow

## 2.1 Registration Process

Anyone can submit a registration request.

However, a newly registered user cannot access protected application functionality until an administrator approves the account.

### Workflow

```text
             USER
               |
               v
       Open Registration
               |
               v
       Enter User Details
               |
               v
       Submit Registration
               |
               v
       Account Pending
               |
               v
      ADMINISTRATOR REVIEW
               |
         -------------
         |           |
         v           v
      APPROVE      REJECT
         |
         v
    Assign Role
         |
         v
    Account Active
         |
         v
    Prism Desk Login
```

## 2.2 Registration Information

The registration form should contain:

- Full name.
- Username.
- Email address.
- Password.
- Confirm password.
- Other required profile information.

## 2.3 Administrator Approval

The administrator dashboard should display pending registrations.

The administrator can:

- View registration details.
- Approve registration.
- Reject registration.
- Assign an appropriate role.

The initial roles are Administrator, Professor, Student and Guest.

## 2.4 Account Status

The following account states will be supported:

- Pending.
- Approved.
- Rejected.
- Deactivated.

Only approved and active accounts can access protected application functionality.

---

# 3. Authentication Workflow

## 3.1 Login

Users can log in using either their registered username or email address.

### Workflow

```text
       OPEN LOGIN PAGE
              |
              v
      Enter Username/Email
              |
              v
         Enter Password
              |
              v
       Submit Login Form
              |
              v
       Backend Validation
              |
        ----------------
        |              |
        v              v
     Invalid         Valid
        |              |
        v              v
   Show Error     Check Account
                       |
                       v
                Check Approval
                       |
                       v
                Create Session
                       |
                       v
                Load Dashboard
```

## 3.2 Password Reset

Users should be able to request a password reset.

The system will verify the user's identity and provide a secure password-reset process.

Reset tokens must expire and must not be reusable.

## 3.3 Automatic Logout

The system will automatically terminate inactive sessions after a configurable period.

Users can also log out manually.

---

# 4. Administrator Workflow

## 4.1 Administrator Dashboard

After login, administrators will access the laboratory-wide dashboard.

The dashboard should display:

- Total users.
- Pending registrations.
- Total professors.
- Total students.
- Total guests.
- Active projects.
- Archived projects.
- Deleted projects.
- Task statistics.
- Research paper statistics.
- Conference deadlines.
- Recent activities.
- System health.
- Database status.

## 4.2 User Management

Administrators can:

1. View all registered users.
2. Review pending registrations.
3. Approve or reject accounts.
4. Assign user roles.
5. Modify user information.
6. Deactivate accounts.
7. Reactivate accounts.
8. Configure guest permissions.

All important administrative changes must be recorded in the activity history.

## 4.3 Project Management

Administrators can:

- Create projects.
- Edit project information.
- Add project members.
- Remove project members.
- Archive projects.
- Delete projects.
- Restore deleted projects.
- Permanently delete projects.

## 4.4 Deleted Projects Management

The administrator can open the Deleted Projects section.

The system should display:

- Project name.
- Project owner.
- Deletion date.
- Deleted by.
- Recovery expiration date.

Available actions:

- Restore.
- Permanently delete.

Deleted projects remain recoverable for 90 days unless an administrator permanently deletes them earlier.

## 4.5 Guest Management

Administrators can:

1. Open the guest management section.
2. Select a guest account.
3. Select the projects the guest can access.
4. Configure permitted features.
5. Set read-only or additional permissions.
6. Save the permission configuration.

The system must immediately enforce the updated permissions.

---

# 5. Professor Workflow

## 5.1 Professor Dashboard

After login, professors will access their dashboard.

It should display:

- Supervised projects.
- Students under supervision.
- Assigned tasks.
- Pending task reviews.
- Student handbook entries.
- Student research paper activity.
- Upcoming task deadlines.
- Conference submission deadlines.
- Recent project activities.

## 5.2 Creating a Research Project

Professors can create research projects.

### Workflow

```text
       Professor Login
              |
              v
       Open Projects
              |
              v
       Create New Project
              |
              v
       Enter Project Details
              |
              v
        Save Project
              |
              v
        Project Created
              |
              v
       Professor Becomes
         Project Owner
```

The project becomes active immediately.

## 5.3 Managing Project Members

Only administrators and professors can manage project membership.

### Workflow

1. Professor opens a project.
2. Opens the Members section.
3. Selects Add Member or Remove Member.
4. Searches for the relevant user.
5. Confirms the action.
6. System updates project membership.
7. Activity history records the change.
8. Relevant Discord notifications are generated according to user preferences.

## 5.4 Assigning Official Tasks

Professors can create official tasks.

### Workflow

```text
       Open Project
            |
            v
       Open Tasks
            |
            v
       Create Task
            |
            v
    Enter Task Information
            |
            v
      Select Students
            |
            v
      Set Deadline
            |
            v
       Save Task
            |
            v
    Create Individual
       Assignments
            |
            v
    Send Notifications
```

Task information includes:

- Task title.
- Description.
- Project.
- Assigned students.
- Priority.
- Deadline.

## 5.5 Assigning One Task to Multiple Students

Example:

A professor assigns a literature review task to three students.

The system creates:

- One common task.
- Three individual student assignments.
- Three independent submission records.

Each student can update their own task status and submit their work independently.

The professor can review each submission separately.

## 5.6 Reviewing Task Submissions

### Workflow

```text
       Student Submits Work
                |
                v
          Under Review
                |
                v
       Professor Opens Task
                |
                v
       Reviews Submission
                |
          -------------
          |           |
          v           v
       Accept      Request Revision
          |           |
          v           v
      Completed   Revision Required
                      |
                      v
                 Student Updates
                    Work
                      |
                      v
                  Resubmits
                      |
                      v
               Professor Reviews
```

The professor can provide text feedback.

Task submissions support text and external links only.

## 5.7 Reviewing Student Handbooks

Professors can access handbook entries for students within their authorised supervision scope.

### Workflow

1. Professor opens the supervised project.
2. Opens the student handbook section.
3. Selects a student.
4. Selects a date.
5. Reads the project-wise entry.
6. Adds a comment.
7. Student receives a Discord notification if enabled.
8. Student can reply to the comment.

Professors cannot edit or delete student handbook entries.

## 5.8 Monitoring Research Paper Activity

Professors can:

- View papers added by students.
- View project research collections.
- View students' reading status.
- Recommend additional papers.
- Add useful research resources.

Professors cannot view students' personal research notes.

## 5.9 Adding Conference Deadlines

Professors can add conference and Call for Papers information.

### Workflow

1. Open a project.
2. Open Conference Tracker.
3. Select Add Conference.
4. Enter conference information.
5. Enter official conference URL.
6. Enter CFP URL.
7. Enter submission deadline.
8. Save the record.

The deadline becomes visible to authorised project members.

---

# 6. Student Workflow

## 6.1 Student Dashboard

After login, students will access their personal research dashboard.

The dashboard should display:

- My projects.
- Assigned tasks.
- Personal tasks.
- Upcoming deadlines.
- Daily handbook.
- Overall daily summary.
- Research paper library.
- Reading status.
- Professor feedback.
- Conference deadlines.
- Recent research activities.

## 6.2 Creating a Research Project

Students can create research projects without administrator or professor approval.

### Workflow

```text
       Student Login
             |
             v
       Open Projects
             |
             v
       Create Project
             |
             v
      Enter Project Details
             |
             v
         Save Project
             |
             v
      Project Active
             |
             v
      Student Becomes
       Project Owner
```

The student becomes the project owner automatically.

However, project ownership does not grant permission to add or remove members.

Administrators and professors retain membership-management privileges.

## 6.3 Participating in Multiple Projects

Students can belong to multiple projects simultaneously.

For each project, they will have separate:

- Task lists.
- Handbook entries.
- Research paper collections.
- Conference deadlines.
- Project activities.

The overall dashboard will combine relevant information across projects.

## 6.4 Creating Personal Tasks

Students can create personal research tasks.

### Workflow

1. Open Personal Tasks.
2. Select Create Task.
3. Enter task title.
4. Enter description.
5. Select priority.
6. Set optional deadline.
7. Associate a project if required.
8. Save the task.

Personal tasks are used for individual research planning.

They are separate from official professor-assigned tasks.

## 6.5 Completing Assigned Tasks

Students can:

1. Open Assigned Tasks.
2. Select a task.
3. Change its status to In Progress.
4. Work on the assigned activity.
5. Enter their submission text.
6. Add external links.
7. Submit the work.
8. Wait for professor review.

File attachments are not supported.

## 6.6 Responding to Revision Requests

If a professor requests a revision:

1. Student receives a notification.
2. Student opens the task.
3. Student reads the professor's feedback.
4. Student updates the submission.
5. Student resubmits the work.
6. Task returns to Under Review.

The professor can then approve the work or request another revision.

---

# 7. Research Paper Management Workflow

## 7.1 Research Library Structure

Prism Desk will provide:

1. Laboratory-wide Research Library.
2. Project-wise Research Libraries.

A research paper can be associated with multiple projects without creating duplicate paper records.

## 7.2 Adding a Research Paper

Students and professors can add research papers.

### Workflow

```text
         Open Research Library
                  |
                  v
             Add Paper
                  |
                  v
         Enter Paper Details
                  |
                  v
         Add External Paper URL
                  |
                  v
          Select Collection
                  |
           ----------------
           |              |
           v              v
       Laboratory       Project
         Library        Library
           |              |
           ----------------
                  |
                  v
             Save Record
                  |
                  v
        Paper Available to
         Authorised Users
```

## 7.3 Research Paper Information

Users can enter:

- Paper title.
- Authors.
- Publication year.
- Journal or conference.
- DOI.
- Abstract.
- Research area.
- Paper URL.

No PDF upload is available.

## 7.4 Sharing Papers Across Projects

A paper already present in the laboratory library can be associated with another project.

The system should create a project association rather than another paper record.

## 7.5 Updating Reading Status

Students can maintain:

- Not Started.
- Reading.
- Completed.

Professors can view reading status within their authorised supervision scope.

## 7.6 Maintaining Personal Research Notes

Students can add private notes to individual papers.

These notes remain accessible only to their owners.

Professors and administrators cannot view them by default.

---

# 8. Daily Research Handbook Workflow

## 8.1 Handbook Structure

Each student maintains:

- One entry per project per day.
- One separate overall daily summary.

## 8.2 Project-wise Entry

### Workflow

```text
       Student Login
             |
             v
       Open Handbook
             |
             v
       Select Project
             |
             v
       Select Date
             |
             v
       Create Daily Entry
             |
             v
       Enter Research Work
             |
             v
            Save
             |
             v
       Entry Available
       for Professor Review
```

Suggested entry fields:

- Research activities.
- Work completed.
- Problems encountered.
- Observations.
- Next planned activities.

## 8.3 Overall Daily Summary

The student separately maintains an overall summary covering research work across all projects.

### Workflow

1. Open Overall Daily Summary.
2. Select date.
3. Enter the day's overall research activities.
4. Save the summary.
5. Edit it whenever necessary.

Only one overall summary per student per date is allowed.

## 8.4 Editing Handbook Entries

Students retain control of their own handbook entries.

They can edit entries even after submission and after professor comments.

The system maintains edit history.

Professors can only comment.

They cannot edit or delete student entries.

## 8.5 Professor Comments and Student Replies

### Workflow

```text
       Student Writes Entry
                |
                v
          Entry Saved
                |
                v
        Professor Reviews
                |
                v
        Professor Comments
                |
                v
        Student Notified
                |
                v
        Student Reads Comment
                |
                v
        Student Replies
                |
                v
        Discussion Continues
```

Comments and replies remain associated with the relevant handbook entry.

---

# 9. Conference and Deadline Tracker Workflow

## 9.1 Purpose

The Conference Tracker helps laboratory members monitor research conference submission deadlines.

## 9.2 Adding a Conference

The following users can add conference records:

- Project owner.
- Assigned professors.
- Any project team member.

### Workflow

1. Open a project.
2. Open Conference Tracker.
3. Select Add Conference.
4. Enter conference name.
5. Enter official website.
6. Enter CFP link.
7. Enter paper submission deadline.
8. Save.

## 9.3 Viewing Deadlines

The project dashboard should display:

- Conference name.
- Submission deadline.
- Associated project.
- Official website.
- CFP link.
- Time remaining.

The overall dashboard should combine conference deadlines across projects accessible to the user.

## 9.4 Deadline Notifications

The system should generate Discord reminders according to the notification preferences configured for each user.

Reminder timing should be configurable.

The exact default reminder schedule will be finalised during feature specification.

---

# 10. Discord Integration Workflow

## 10.1 Connecting Discord

Each user can link their individual Discord account with Prism Desk.

### Workflow

```text
        User Login
             |
             v
        Open Settings
             |
             v
       Connect Discord
             |
             v
      Discord Authorisation
             |
             v
       Verify Account Link
             |
             v
       Save Discord Mapping
             |
             v
       Integration Active
```

The implementation should use a secure account-verification mechanism.

## 10.2 Project Discord Channels

The laboratory Discord server may contain:

- General laboratory channels.
- Announcement channels.
- Research discussion channels.
- Project-specific channels.
- Voice discussion channels.

Channel access must follow Discord server permissions.

## 10.3 Communication Policy

Discord is the only communication platform for Prism Desk.

The application will not implement a separate internal messaging or chat module in the initial version.

## 10.4 Attachment Policy

Users can share screenshots and attachments directly through Discord.

Prism Desk must never download, copy or store those attachments.

---

# 11. Notification Workflow

## 11.1 Notification Events

Discord notifications will be generated for:

- New task assignments.
- Approaching deadlines.
- Task submissions.
- Professor handbook comments.
- Student replies.
- New research papers.
- New projects.
- Project membership changes.
- Laboratory announcements.

## 11.2 Notification Preferences

All relevant notification events will be enabled by default.

Users can independently disable individual event categories.

### Workflow

1. User opens Notification Settings.
2. User views notification categories.
3. User enables or disables individual categories.
4. System saves preferences.
5. Notification service checks preferences before sending messages.

## 11.3 Notification Failure

If Discord is unavailable:

- Prism Desk operations continue.
- Database records are saved normally.
- Failed notifications are logged.
- Notification delivery can be retried.

---

# 12. Guest Workflow

## 12.1 Guest Access

Guests can access only resources authorised by administrators.

### Workflow

```text
       Guest Registration
                |
                v
        Administrator Approval
                |
                v
         Assign Guest Role
                |
                v
       Configure Permissions
                |
                v
        Select Projects
                |
                v
         Grant Permissions
                |
                v
           Guest Login
                |
                v
       Access Permitted Areas
```

## 12.2 Guest Restrictions

Guests cannot automatically access:

- All laboratory projects.
- All student handbooks.
- Private research notes.
- Administrative dashboards.
- Other restricted information.

Any additional permission must be explicitly granted.

---

# 13. Project Lifecycle Workflow

## 13.1 Project States

Projects can have three states:

- Active.
- Archived.
- Deleted.

## 13.2 Archiving

When a project is completed:

1. Administrator or appropriately authorised user opens the project.
2. Selects Archive.
3. Confirms the operation.
4. Project status changes to Archived.
5. Project history remains available.
6. Project disappears from active project lists.

The exact archive permission for students and professors will follow the final project-permission rules.

## 13.3 Deletion

Only administrators can delete projects.

### Workflow

```text
         Active Project
               |
               v
       Administrator Selects
              Delete
               |
               v
        Confirmation Screen
               |
               v
         Project Deleted
               |
               v
         Deleted Items Area
               |
        ---------------------
        |                   |
        v                   v
      Restore         Permanent Delete
        |                   |
        v                   v
   Active Project      Records Removed
```

Deleted projects remain recoverable for 90 days unless permanently deleted earlier by an administrator.

All associated records must be handled according to the safe-deletion policy.

Shared research papers must not be deleted if they are still associated with other projects or the laboratory library.

---

# 14. Activity History Workflow

The system will automatically record important activities.

Examples:

- User registration.
- Account approval.
- Role changes.
- Project creation.
- Project membership changes.
- Task assignments.
- Task status updates.
- Research paper additions.
- Handbook edits.
- Conference additions.
- Project archiving.
- Project deletion.
- Project restoration.

### Workflow

```text
          User Performs Action
                   |
                   v
             FastAPI Backend
                   |
                   v
             Validate Action
                   |
                   v
              Save Record
                   |
                   v
             Audit Service
                   |
                   v
              Activity Log
```

Users will see only the activity information permitted by their roles.

Private research notes must not appear in audit logs.

---

# 15. Cross-Module Workflow Example

This section describes how the different modules work together during a typical research project.

### Example: Literature Review Research Project

**Step 1: Project creation**

A student creates a new literature review project.

The project becomes active immediately.

The student automatically becomes the project owner.

**Step 2: Professor supervision**

An administrator or professor adds the supervising professor and other students to the project.

**Step 3: Research paper collection**

Students and professors add relevant research papers to the project library.

**Step 4: Task assignment**

The professor assigns a literature review task to three students.

**Step 5: Individual research work**

Each student works independently and maintains their task status.

**Step 6: Task submission**

Each student submits text and relevant external links.

**Step 7: Professor review**

The professor reviews the submissions and requests revisions where necessary.

**Step 8: Daily handbook**

Each student maintains a separate project-wise daily entry and an overall daily summary.

**Step 9: Professor feedback**

The professor comments on handbook entries.

Students can reply and continue editing their own entries.

**Step 10: Conference tracking**

A project member adds an upcoming conference and its CFP deadline.

**Step 11: Discord communication**

The team discusses research problems and shares screenshots through the project's Discord channel.

**Step 12: Project completion**

When the research project finishes, it can be archived while retaining its records.

---

# 16. Workflow Design Principles

The following principles must guide implementation:

1. Each user must interact only with authorised application features.
2. Project creation must not require approval.
3. Project creators automatically become project owners.
4. Only administrators and professors can manage project membership.
5. Students can participate in multiple projects.
6. Multiple professors can supervise one project.
7. Every student assigned a common task must have an individual assignment and submission.
8. Students retain editing control over their handbook entries.
9. Professors can comment but cannot modify student entries.
10. Personal research notes remain private.
11. Research papers can be shared across projects.
12. Conference deadlines can be added by project members.
13. Discord handles communication and notifications.
14. Prism Desk never stores file attachments.
15. Database records remain the source of truth.
16. Important activities must be recorded in the audit history.

---

# 17. Workflow Acceptance Criteria

The workflows will be considered ready for implementation when:

- Registration and administrator approval work.
- Users can log in using email or username.
- Each role receives the correct dashboard.
- Students can create projects immediately.
- Project creators become owners automatically.
- Project membership restrictions work.
- Research papers can be shared across projects.
- Task assignments support multiple students.
- Individual submissions are maintained.
- Task review and revision workflows function.
- Students can edit handbook entries.
- Professors can comment and students can reply.
- Conference deadlines can be created and tracked.
- Discord account linking works.
- Notification preferences are respected.
- Guest permissions are enforced.
- Projects can be archived, deleted and restored.
- Activity history is maintained.
- No file attachments are uploaded or stored.

---

# 18. Final Workflow Statement

Prism Desk will provide a structured research workflow connecting project creation, membership management, research paper organisation, task assignment, daily handbook maintenance, professor feedback and conference deadline tracking.

Discord will provide communication and notifications, while PostgreSQL will maintain the application's structured research records.

The workflow will preserve student control over personal research notes and daily handbooks while providing professors with the necessary research supervision capabilities.

**Document Status:** User Workflows Specification – Version 1.0.