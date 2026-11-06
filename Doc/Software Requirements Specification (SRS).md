# PRISM DESK
## Software Requirements Specification (SRS)

**Project Name:** Prism Desk  
**Laboratory:** PRISM Laboratory  
**Document:** Software Requirements Specification  
**Version:** 1.0  
**Phase:** Phase 0 – Requirements Analysis  
**Status:** Initial Requirements Baseline

**Tagline:** One Lab. Multiple Projects. Connected Research.

---

# 1. Introduction

## 1.1 Purpose

Prism Desk is a web-based Laboratory Management and Research Collaboration System designed for the PRISM Laboratory.

The purpose of this application is to provide a central platform where laboratory administrators, professors, students and approved guests can manage research activities, coordinate projects, organise research papers, assign tasks and monitor research progress.

The system will simplify research management by bringing important laboratory activities into one organised platform.

Discord will be integrated for communication and notifications, while Prism Desk will maintain structured research records in its database.

## 1.2 Problem Statement

Research laboratories often manage their activities using multiple disconnected platforms, including:

- Discord and other messaging applications.
- Google Docs and spreadsheets.
- Research paper websites.
- Personal notebooks and diaries.
- Separate task management tools.
- Manually maintained project records.

This creates several problems:

1. Research information becomes scattered across different platforms.
2. Professors have difficulty monitoring student research activities.
3. Students may struggle to organise work across multiple projects.
4. Research papers and resources are difficult to track centrally.
5. Task assignments and deadlines may be overlooked.
6. Daily research progress is not maintained consistently.
7. Historical research activities are difficult to retrieve.

Prism Desk aims to address these problems through a centralised research management platform.

## 1.3 Project Objectives

The primary objectives are:

1. Provide a centralised laboratory management platform.
2. Support multiple research projects simultaneously.
3. Allow students to participate in multiple projects.
4. Enable professors to supervise multiple projects and students.
5. Maintain a common laboratory research library.
6. Maintain separate research paper collections for individual projects.
7. Provide structured task assignment and tracking.
8. Maintain project-wise daily research handbooks.
9. Provide an overall daily research summary for each student.
10. Integrate Discord for communication and notifications.
11. Track conference names and Call for Papers deadlines.
12. Provide role-specific dashboards.
13. Maintain project history and activity records.
14. Minimise server storage requirements by avoiding file uploads.

## 1.4 Scope

Prism Desk will initially support approximately 30 laboratory users.

The system will be hosted on a laboratory workstation and accessed through web browsers over the laboratory network.

The application will use a local PostgreSQL database.

The initial version will not provide file-upload or file-storage functionality.

---

# 2. User Roles and Responsibilities

Prism Desk will support four user roles.

## 2.1 Administrator

Administrators are responsible for managing the overall application.

Two administrators are expected initially: the user and the professor.

Responsibilities:

- Approve new user registrations.
- Manage user accounts.
- Assign and modify user roles.
- Create and manage research projects.
- Add and remove project members.
- Manage guest permissions.
- Monitor laboratory activities.
- View laboratory-wide dashboards.
- Manage archived and deleted projects.
- Restore deleted projects.
- Permanently delete projects.
- Monitor system activity and audit history.

## 2.2 Professor

Professors supervise research projects and monitor student progress.

Responsibilities:

- Create research projects.
- Participate in multiple research projects.
- Supervise multiple students.
- Add or remove project members.
- Assign tasks to individual or multiple students.
- Review student task submissions.
- Provide task feedback.
- View student research handbooks.
- Comment on handbook entries.
- Monitor students' research paper reading status.
- Add and recommend research papers.
- Add conference deadlines.
- Monitor project progress.

Professors cannot directly modify student handbook entries.

## 2.3 Student

Students perform research activities and maintain their research records.

Responsibilities:

- Create research projects.
- Participate in multiple projects.
- Maintain project-wise daily handbooks.
- Maintain overall daily summaries.
- Edit their own handbook entries.
- Reply to professor comments.
- Add research papers and resources.
- Maintain personal research notes.
- Update paper reading status.
- Complete assigned tasks.
- Create personal research tasks.
- Submit task responses using text and external links.
- View project announcements and resources.
- Access Discord communication channels.

Students cannot independently add or remove project members.

## 2.4 Guest

Guests are external or temporary users who may require limited access to laboratory resources.

Guest permissions will be configurable by administrators.

Administrators can control:

- Project visibility.
- Research paper visibility.
- Resource access.
- Discussion access.
- Read-only permissions.
- Other explicitly authorised actions.

Guest accounts will not automatically receive student or professor privileges.

---

# 3. User Registration and Authentication

## 3.1 Registration

The application will allow users to register using a registration form.

However, newly registered accounts will remain inactive until approved by an administrator.

Registration workflow:

1. User opens the registration page.
2. User enters the required information.
3. User submits the registration request.
4. The account enters pending approval status.
5. Administrator reviews the request.
6. Administrator approves or rejects the registration.
7. Approved users can access Prism Desk.

## 3.2 Login

Users can authenticate using either:

- Registered email address.
- Registered username.

Both methods will use password authentication.

## 3.3 Security Requirements

The authentication system must support:

- Secure password hashing.
- Password reset functionality.
- Automatic logout after inactivity.
- Role-based access control.
- Account approval before access.
- Secure session management.

---

# 4. Project Management Module

## 4.1 Project Creation

All three primary roles can create research projects:

- Administrator.
- Professor.
- Student.

A newly created project becomes active immediately.

No administrator or professor approval is required.

## 4.2 Project Ownership

The person creating a project automatically becomes its project owner.

The project owner is responsible for coordinating project activities.

## 4.3 Project Membership

Only administrators and professors can add or remove project members.

The system must support:

- Multiple students in one project.
- Multiple professors supervising one project.
- One student participating in multiple projects.
- One professor supervising multiple projects.

## 4.4 Project Information

Each project should maintain:

- Project title.
- Project description.
- Research objectives.
- Project owner.
- Assigned professors.
- Project members.
- Creation date.
- Start date.
- Expected completion date.
- Project status.
- Associated research papers.
- Associated tasks.
- Conference deadlines.

## 4.5 Project Status

Projects will support three major states.

**Active**

The project is currently running.

**Archived**

The project has finished or is no longer active.

Its associated research records must remain accessible.

**Deleted**

The project has been moved to the Deleted Items area.

Administrators can restore it or permanently delete it.

## 4.6 Safe Project Deletion

Deleted projects must remain recoverable for 90 days.

Administrators can:

- View deleted projects.
- Restore deleted projects.
- Permanently delete projects before the retention period expires.

The deletion process must also account for associated project records, including tasks, research paper associations, discussions, conference records and handbook history.

Permanent deletion must require administrator confirmation.

---

# 5. Research Paper and Resource Management

## 5.1 Research Library

Prism Desk will provide two connected research collections.

### A. Laboratory Research Library

A common research library accessible to laboratory members.

Users can:

- Add research papers.
- Search papers.
- Browse research resources.
- View paper metadata.
- Associate papers with research projects.

### B. Project-wise Research Library

Each project will have its own research paper collection.

Project members can:

- View project papers.
- Add research paper links.
- Track reading progress.
- Add personal research notes.
- Access associated research resources.

## 5.2 Research Paper Information

Each paper record should support:

| Field | Description |
|---|---|
| Paper ID | Unique identifier |
| Paper title | Full paper title |
| Authors | Author information |
| Publication year | Publication year |
| Journal/Conference | Publication venue |
| DOI | Digital Object Identifier |
| Paper URL | External paper link |
| Research area | Research topic |
| Added by | User who added the paper |
| Added date | Date of addition |
| Reading status | Current reading status |
| Associated projects | Linked research projects |

## 5.3 Reading Status

Students can maintain the following statuses:

- Not Started.
- Reading.
- Completed.

The status should be editable by the student.

## 5.4 Personal Research Notes

Students can maintain personal notes associated with research papers.

These notes are private.

Professors and administrators must not be able to view students' personal paper notes by default.

## 5.5 Research Paper Visibility

The system will support:

- Laboratory-wide paper visibility.
- Project-specific paper visibility.

Project papers will be accessible to members of the associated project.

A paper should be stored once in the database and linked to multiple projects when necessary.

## 5.6 Professor Monitoring

Professors can view:

- Papers added by students.
- Students' reading status.
- Project research paper collections.

Professors cannot view students' personal research notes.

---

# 6. Task Management Module

## 6.1 Task Creation

Two categories of tasks will be supported.

### Official Project Tasks

Created by administrators and professors.

These tasks can be assigned to one or multiple students.

### Personal Research Tasks

Created by students for their own research tracking.

These tasks do not require professor assignment.

## 6.2 Task Information

Each task should contain:

- Task title.
- Task description.
- Associated project.
- Assigned students.
- Created by.
- Creation date.
- Start date.
- Deadline.
- Priority.
- Task status.
- Submission information.
- Review comments.

## 6.3 Multiple Student Assignment

Professors can assign one task to multiple students.

Each student must maintain an individual task submission.

For example:

A professor assigns a literature review task to three students.

The system must maintain:

- One common task definition.
- Three individual student assignments.
- Three independent submission records.
- Individual review status for each student.

## 6.4 Task Workflow

The task lifecycle will follow:

1. To Do.
2. In Progress.
3. Under Review.
4. Revision Required.
5. Completed.

The system must allow a submitted task to return to Revision Required when further work is necessary.

## 6.5 Task Submission

Students can submit tasks using:

**Text submissions**

- Research explanations.
- Literature review summaries.
- Progress reports.
- Answers and observations.

**External links**

- Google Drive links.
- GitHub repositories.
- Research paper URLs.
- Websites.
- Other online resources.

File attachments are not supported.

## 6.6 Task Review

Professors can:

- Review student submissions.
- Add feedback.
- Request revisions.
- Mark submissions as completed.

Each student's submission must be reviewed independently.

---

# 7. Daily Research Handbook

## 7.1 Purpose

The Daily Research Handbook will maintain a structured record of student research activities.

It will provide professors with visibility into students' daily research progress.

## 7.2 Handbook Structure

Each student will maintain:

1. Project-wise daily entries.
2. One overall daily summary.

### Project-wise Entries

One daily entry for each project in which the student participates.

Suggested fields:

- Date.
- Project.
- Research activities.
- Work completed.
- Problems encountered.
- Observations.
- Next planned activities.

### Overall Daily Summary

A separate summary covering the student's complete research activities across all projects.

## 7.3 Editing Permissions

Students have complete editing control over their own handbook entries.

Students can:

- Create entries.
- Edit entries.
- Update submitted entries.
- Maintain their overall daily summary.

Professors can:

- View student entries.
- Comment on individual entries.

Professors cannot:

- Edit student entries.
- Delete student entries.
- Rewrite student research records.

## 7.4 Comment and Reply System

The handbook will support a comment-based feedback system.

Workflow:

1. Student writes a handbook entry.
2. Professor reads the entry.
3. Professor adds a comment.
4. Student views the comment.
5. Student replies.
6. Further discussion can continue through replies.

## 7.5 Edit History

The system should maintain an edit history for handbook entries.

This will allow the laboratory to track changes made to research records over time.

---

# 8. Discord Integration

## 8.1 Purpose

Discord will be the primary communication platform for PRISM Laboratory.

Prism Desk will not implement a separate internal chat system in the initial version.

## 8.2 Integration Requirements

The system should support:

- Laboratory Discord server integration.
- Individual Discord account linking.
- Project-specific Discord channels.
- User-to-Discord account mapping.
- Discord notifications.
- Appropriate channel and role permissions.

## 8.3 Discord Communication

Discord will support:

- Laboratory announcements.
- Project discussions.
- Research discussions.
- Student-professor communication.
- Sharing screenshots.
- Sharing external links.
- Quick research updates.

## 8.4 File Storage Restriction

Discord may be used to share screenshots and other attachments for communication.

However, Prism Desk must not:

- Download Discord attachments.
- Copy Discord files to its workstation.
- Store Discord screenshots.
- Maintain local copies of shared documents.
- Use Discord as a file-storage backend.

Discord manages its own messages and attachments according to its platform policies.

Prism Desk will only maintain the structured research information required by the application.

---

# 9. Notification System

## 9.1 Notification Channel

Discord will be the notification channel for Prism Desk.

The system will support configurable notification preferences.

## 9.2 Notification Events

Notifications should be generated for:

1. New task assignment.
2. Approaching task deadlines.
3. Task submission.
4. Professor comments on handbook entries.
5. Student replies to professor comments.
6. New research papers.
7. New project creation.
8. Project member additions.
9. Project member removals.
10. Laboratory announcements.

## 9.3 User Preferences

Relevant notifications will be enabled by default.

Users can independently disable notifications for individual event types.

Notification preferences must be maintained per user.

---

# 10. Conference and Call for Papers Deadline Tracker

## 10.1 Purpose

The system will include a dedicated Conference and Deadline Tracker.

This module will help laboratory members monitor upcoming research conference submission deadlines.

## 10.2 Conference Information

Each conference record should support:

| Field | Description |
|---|---|
| Conference ID | Unique identifier |
| Conference name | Name of the conference |
| Conference website | Official conference URL |
| CFP link | Call for Papers URL |
| Submission deadline | Final paper submission date |
| Associated project | Related research project |
| Added by | User who created the record |
| Creation date | Date of addition |

## 10.3 Permissions

The following users can add conference deadlines:

- Project owner.
- Assigned professors.
- Any member of the associated project.

## 10.4 Deadline Monitoring

The dashboard should display:

- Upcoming conference deadlines.
- Conference names.
- Submission dates.
- Associated projects.
- Time remaining until submission.

Discord reminders should be supported through the notification system.

---

# 11. Dashboard and Analytics

Prism Desk will provide different dashboards based on user roles.

## 11.1 Administrator Dashboard

The administrator dashboard should include:

- Total laboratory users.
- Total professors.
- Total students.
- Total guests.
- Active projects.
- Archived projects.
- Deleted projects.
- Task completion statistics.
- Research paper statistics.
- Student activity overview.
- Conference deadlines.
- Recent system activities.
- Registration requests.
- System health.
- Database status.

## 11.2 Professor Dashboard

The professor dashboard should include:

- Supervised projects.
- Students under supervision.
- Assigned tasks.
- Pending task reviews.
- Student handbook entries.
- Student research paper activity.
- Upcoming deadlines.
- Conference submission deadlines.
- Project progress.
- Recent student activities.

## 11.3 Student Dashboard

The student dashboard should include:

- My projects.
- Assigned tasks.
- Personal research tasks.
- Upcoming deadlines.
- Daily research handbook.
- Overall daily summary.
- Research paper library.
- Reading status.
- Professor feedback.
- Conference deadlines.
- Overall research progress.

## 11.4 Guest Dashboard

The guest dashboard should display only information permitted by the administrator.

---

# 12. Activity History and Audit System

## 12.1 Purpose

Prism Desk will maintain a record of important application activities.

This will help administrators understand changes made within the system.

## 12.2 Activities to Record

The system should record:

- Project creation.
- Project updates.
- Project archiving.
- Project deletion.
- Project restoration.
- Task creation.
- Task updates.
- Task status changes.
- Research paper additions.
- Research paper updates.
- Handbook creation.
- Handbook edits.
- Project membership changes.
- Account approval.
- User role changes.
- Important administrative actions.

## 12.3 Audit Information

Each audit record should contain:

- Activity ID.
- User ID.
- Activity type.
- Associated project or record.
- Timestamp.
- Relevant change information.

Audit records should not expose students' private research notes.

---

# 13. Database Requirements

## 13.1 Database Technology

PostgreSQL will be used as the primary database.

SQLAlchemy will provide database interaction through the FastAPI backend.

Alembic will manage database schema migrations.

## 13.2 Data Organisation

Each research project will maintain independent:

- Project membership records.
- Tasks.
- Task submissions.
- Daily handbook entries.
- Project discussions and associated records.
- Conference deadline records.

Research papers and selected resources can be associated with multiple projects.

The laboratory-wide Research Library will provide common access to shared papers.

## 13.3 Important Database Entities

The initial database design should consider the following entities:

1. Users.
2. Roles.
3. Registration Requests.
4. Projects.
5. Project Members.
6. Research Papers.
7. Paper-Project Associations.
8. Reading Status.
9. Personal Research Notes.
10. Tasks.
11. Task Assignments.
12. Task Submissions.
13. Task Reviews.
14. Daily Handbooks.
15. Handbook Comments.
16. Handbook Replies.
17. Handbook Edit History.
18. Conference Records.
19. Notification Preferences.
20. Discord Account Links.
21. Activity Logs.
22. Deleted Project Records.

The final table structure and relationships will be defined in the Database Design document.

---

# 14. File and Storage Policy

## 14.1 Strict No-Upload Policy

Prism Desk will not provide file-upload functionality.

The application must not store:

- PDF files.
- Word documents.
- PowerPoint files.
- Images.
- Screenshots.
- Videos.
- Audio files.
- ZIP archives.
- Datasets.
- Other file attachments.

## 14.2 Permitted Data

The application may store:

- Text.
- URLs.
- Research paper metadata.
- Task descriptions.
- Handbook entries.
- Comments.
- Notifications.
- User information.
- Project information.

## 14.3 Discord Exception

Users can share screenshots and files through Discord.

However, Prism Desk will not copy or store these attachments.

---

# 15. Non-Functional Requirements

## 15.1 Performance

The system should support approximately 30 laboratory users.

Common operations should respond quickly under normal laboratory network conditions.

## 15.2 Security

The application must implement:

- Password hashing.
- Role-based access control.
- Secure session management.
- Registration approval.
- Protected administrative operations.
- Restricted project access.
- Secure Discord account mapping.

## 15.3 Reliability

The application should maintain reliable access to research records.

Database backup and recovery mechanisms must be implemented.

## 15.4 Backup

PostgreSQL data must be backed up automatically every day.

Initially, backups will be stored on the laboratory workstation.

An external backup strategy should be considered in a later deployment improvement.

## 15.5 Scalability

The architecture should support:

- More students.
- More professors.
- More research projects.
- Additional laboratory modules.

## 15.6 Maintainability

The application should use modular architecture with separate frontend, backend and database layers.

## 15.7 Accessibility

The application should support modern desktop and mobile web browsers.

## 15.8 Storage Efficiency

The system must avoid file uploads and unnecessary storage consumption.

---

# 16. Technology Stack

The selected technology stack is:

| Component | Technology |
|---|---|
| Operating System | Ubuntu Linux |
| Frontend | React |
| Programming Language | TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| Backend | Python |
| Backend Framework | FastAPI |
| API Server | Uvicorn |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Validation | Pydantic |
| API Documentation | Swagger/OpenAPI |
| Communication | Discord |
| Version Control | Git |
| Containerisation | Docker |
| Deployment | Docker Compose |
| Reverse Proxy | Nginx |
| Backend Testing | Pytest |

The application will initially run on a laboratory workstation and be accessed over the laboratory network.

---

# 17. System Architecture

Prism Desk will use a modular monolithic architecture.

The system will consist of three primary application layers.

## 17.1 Presentation Layer

React frontend responsible for:

- User interface.
- Dashboards.
- Forms.
- Research library.
- Task management.
- Handbook interface.
- Conference tracker.
- User management.

## 17.2 Application Layer

FastAPI backend responsible for:

- Authentication.
- Authorisation.
- Business logic.
- Project management.
- Task processing.
- Handbook management.
- Research paper management.
- Discord integration.
- Notification processing.

## 17.3 Data Layer

PostgreSQL responsible for maintaining:

- User information.
- Project information.
- Research records.
- Task records.
- Handbook records.
- Conference information.
- Activity history.
- Notification preferences.

## 17.4 High-Level Architecture

```text
             LABORATORY USERS
                    |
                    |
              WEB BROWSER
                    |
                    |
             REACT FRONTEND
                    |
                    |
             FASTAPI BACKEND
                    |
          ---------------------
          |         |         |
          |         |         |
      AUTH       BUSINESS   DISCORD
      MODULE      LOGIC     INTEGRATION
          |         |         |
          |         |         |
          ---------------------
                    |
                    |
                POSTGRESQL
                    |
          ---------------------
          |         |         |
        USERS    PROJECTS   RESEARCH
          |         |         |
         TASKS   HANDBOOK   AUDIT LOGS
```

Discord will be an external integration rather than the primary database.

---

# 18. Initial Acceptance Criteria

The initial Prism Desk release will be considered functionally acceptable when the following conditions are satisfied.

### User Management

- Users can register.
- Administrators can approve registrations.
- Users can log in using email or username.
- Role-based permissions work correctly.
- Password reset works.

### Project Management

- All primary roles can create projects.
- Student-created projects become active immediately.
- Project creators become project owners.
- Students can participate in multiple projects.
- Multiple professors can supervise projects.
- Only administrators and professors can manage membership.
- Projects can be archived and safely deleted.

### Research Library

- Laboratory-wide research library works.
- Project-wise paper collections work.
- Papers can be associated with multiple projects.
- Students can maintain reading status.
- Personal notes remain private.

### Task Management

- Professors and administrators can create official tasks.
- Students can create personal tasks.
- Tasks can be assigned to multiple students.
- Each student has an individual submission.
- Text and external links are supported.
- Task review and revision workflows work.

### Daily Handbook

- Students can create project-wise entries.
- Students can create overall daily summaries.
- Students can edit their entries.
- Professors can comment.
- Students can reply.
- Handbook edit history is maintained.

### Discord Integration

- Laboratory Discord server can be connected.
- Individual accounts can be linked.
- Discord notifications work.
- User notification preferences work.
- Prism Desk does not store Discord attachments.

### Conference Tracker

- Users with the permitted project roles can add conference records.
- Conference submission deadlines are displayed.
- Upcoming deadlines can trigger notifications.

### Security and Storage

- Role-based access control works.
- Guest permissions are configurable.
- Daily database backups work.
- No file-upload functionality exists.

---

# 19. Future Development

The following features are outside the initial implementation scope but may be considered later.

1. AI-based research paper recommendations.
2. AI-based handbook summaries.
3. Semantic research paper search.
4. Automated weekly and monthly research reports.
5. Advanced research analytics.
6. GitHub integration.
7. Advanced Discord bot commands.
8. Research meeting scheduler.
9. Conference recommendation system.
10. Export of research reports to PDF, CSV and Excel.

These features should be considered only after the core application is stable.

---

# 20. Phase 0 Completion Statement

The Phase 0 Requirements Analysis establishes the functional scope, user roles, application modules, data requirements, technology stack and high-level architecture of Prism Desk.

The system is intended to provide a centralised research management environment for the PRISM Laboratory.

The initial implementation will focus on user management, project management, research paper organisation, task tracking, daily research handbooks, Discord integration and conference deadline monitoring.

The system will use a local PostgreSQL database hosted on the laboratory workstation.

No file attachments will be uploaded or stored by Prism Desk.

This document will serve as the primary requirements reference for the subsequent system design and implementation phases.

**Document Status:** SRS Version 1.0 – Initial Requirements Baseline.