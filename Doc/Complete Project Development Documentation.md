# PRISM DESK
## Complete Project Development Documentation
### PRISM Laboratory Management & Research Collaboration Platform

**Project Name:** Prism Desk  
**Laboratory:** PRISM  
**Project Type:** Web-Based Laboratory Management and Research Collaboration System  
**Version:** 1.0  
**Architecture:** Modular Monolithic Architecture  
**Deployment:** Self-Hosted on Laboratory Workstation  
**Primary Users:** Administrators, Professors and Students

---

# TABLE OF CONTENTS

1. Project Overview
2. Project Objectives
3. User Roles and Responsibilities
4. Technology Stack
5. System Architecture
6. Phase 0 – Requirement Analysis and System Design
7. Phase 1 – Development Environment Setup
8. Phase 2 – Backend Foundation and Database Design
9. Phase 3 – Authentication and User Management
10. Phase 4 – Research Project Management
11. Phase 5 – Research Paper and Resource Management
12. Phase 6 – Task Management and Assignment System
13. Phase 7 – Daily Research Handbook
14. Phase 8 – Communication and Discussion System
15. Phase 9 – Discord Integration
16. Phase 10 – Dashboards and Research Analytics
17. Phase 11 – Testing, Security and Quality Assurance
18. Phase 12 – Workstation Deployment
19. Phase 13 – Advanced Features and Future Development
20. Database Design Overview
21. Security Requirements
22. Storage Management Strategy
23. Codex Development Workflow
24. Final Project Deliverables
25. Development Roadmap and Completion Criteria

---

# 1. PROJECT OVERVIEW

Prism Desk is a centralized web-based laboratory management and research collaboration platform developed for the PRISM laboratory.

The laboratory consists of approximately 30 users, including professors, students and other research members. Students work on different research projects under the supervision of professors.

Currently, research communication, paper sharing, task assignments and daily research records can become distributed across different platforms.

Prism Desk aims to bring these activities into one centralized system.

The platform will allow professors to supervise research activities, assign tasks, share research papers, monitor student progress and communicate with students.

Students will be able to manage their research projects, maintain daily research handbooks, share research papers, receive assignments and submit completed work.

The application will be hosted on a laboratory workstation using a locally maintained PostgreSQL database.

Research paper PDFs will not be stored on the workstation. Instead, the application will maintain paper URLs, DOI information, metadata, notes and discussions.

Discord will be integrated as an optional communication and notification platform.

## 1.1 Core Concept

Prism Desk will function as a digital workspace for the entire laboratory.

Its primary modules will include:

- User and Role Management
- Research Project Management
- Research Paper Library
- Task and Assignment Management
- Daily Research Handbook
- Professor-Student Communication
- Project Discussions
- Discord Integration
- Research Progress Monitoring
- Reports and Analytics

---

# 2. PROJECT OBJECTIVES

The primary objectives are:

1. Develop a centralized management system for laboratory activities.
2. Allow professors to manage multiple research projects.
3. Allow students to participate in multiple research projects.
4. Provide a common platform for sharing research papers and website resources.
5. Enable professors to assign tasks and monitor completion.
6. Provide students with a digital daily research handbook.
7. Allow professors to review student handbooks and provide feedback.
8. Maintain project-specific research discussions.
9. Integrate Discord for notifications and communication.
10. Monitor student and project progress.
11. Maintain research records using a local PostgreSQL database.
12. Minimize workstation storage consumption.

## 2.1 Expected Users

| User Type | Approximate Number | Responsibilities |
|---|---:|---|
| Administrator | 1–2 | Platform management |
| Professor | Initially 1 | Research supervision |
| Students | Approximately 20 | Research activities |
| Other Members | Remaining users | According to assigned permissions |

The architecture must support additional professors, students and projects without requiring major structural changes.

---

# 3. USER ROLES AND RESPONSIBILITIES

Prism Desk will initially support three primary roles.

## 3.1 Administrator

The administrator manages the entire application.

Permissions:

- Create user accounts.
- Add professors.
- Add students.
- Edit user information.
- Activate or deactivate accounts.
- Assign professors to projects.
- Manage project memberships.
- Manage user roles.
- Monitor laboratory activity.
- Manage system settings.
- Review audit logs.
- Manage database backup procedures.

## 3.2 Professor

Professors supervise research projects and students.

Permissions:

- Create research projects.
- Edit project information.
- Add students to projects.
- Assign project supervisors.
- Share research papers.
- Share website resources.
- Assign tasks.
- Set task deadlines.
- Review task submissions.
- Provide feedback.
- View assigned students' handbooks.
- Comment on handbook entries.
- Participate in project discussions.
- Monitor research progress.
- Publish announcements.

A professor should only access information permitted by their assigned responsibilities.

## 3.3 Student

Students use Prism Desk to manage their research activities.

Permissions:

- View assigned projects.
- View project members.
- Share research papers.
- Share useful websites.
- Maintain reading lists.
- Receive tasks.
- Update task progress.
- Submit completed work.
- Maintain daily research handbooks.
- Participate in project discussions.
- Communicate with professors.
- View professor feedback.
- Receive notifications.

Students should not automatically have access to another student's private handbook or submissions.

---

# 4. TECHNOLOGY STACK

The following technology stack will be used.

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
| Database Migration | Alembic |
| Data Validation | Pydantic |
| Authentication | Secure session-based authentication |
| API Documentation | Swagger / OpenAPI |
| Communication Integration | Discord Webhooks and Bot |
| Version Control | Git |
| Repository Hosting | GitHub |
| Containerization | Docker |
| Container Orchestration | Docker Compose |
| Reverse Proxy | Nginx |
| Testing | Pytest and frontend testing tools |

## 4.1 Architectural Approach

Prism Desk will use a modular monolithic architecture.

The frontend, backend and database will be separate components, but the backend will remain one application organized into independent modules.

Microservices are unnecessary for the expected initial user base.

---

# 5. SYSTEM ARCHITECTURE

The application will be hosted on the laboratory workstation.

## 5.1 High-Level Architecture

```text
                 PRISM DESK
                      |
              WEB APPLICATION
                      |
              REACT FRONTEND
                      |
                 FASTAPI
                      |
          +-----------+-----------+
          |           |           |
       AUTH       BUSINESS     DISCORD
       MODULE      LOGIC      INTEGRATION
          |           |
          +-----------+
                      |
                 SQLALCHEMY
                      |
                 POSTGRESQL
                      |
             LOCAL WORKSTATION
```

## 5.2 User Access

Professors and students will access Prism Desk through their browsers.

Example:

http://192.168.1.100

The actual IP address will depend on the workstation's network configuration.

The database will not be directly accessible to student computers.

Only the backend will communicate with PostgreSQL.

---

# PHASE 0 – REQUIREMENT ANALYSIS AND SYSTEM DESIGN

## Objective

Finalize the complete functional and technical requirements before implementation.

## 0.1 Requirement Collection

Document the expected functionality for:

- Administrators.
- Professors.
- Students.
- Research projects.
- Research paper sharing.
- Task assignments.
- Daily handbooks.
- Communication.
- Discord integration.
- Reports and analytics.

## 0.2 User Relationship Design

The database must support the following relationships:

- One professor can supervise multiple projects.
- One project can have multiple professors.
- One project can contain multiple students.
- One student can participate in multiple projects.
- One professor can supervise multiple students.
- One student can have different responsibilities in different projects.

These relationships must be implemented using appropriate relational database tables.

## 0.3 Handbook Visibility

Recommended default:

- Students can view and edit their own entries.
- Assigned professors can review their students' entries.
- Other students cannot access private handbook entries.
- Project-level sharing can be introduced through explicit permissions.

## 0.4 Research Paper Visibility

When a student adds a paper, they should be able to select its visibility:

- Private.
- Shared with professor.
- Shared with project members.
- Shared with the entire laboratory.

## 0.5 Communication Design

Communication should be divided into:

1. Project discussions.
2. Individual professor-student conversations.
3. Task-related comments.
4. Paper-related discussions.
5. Laboratory announcements.

## Deliverables

- Software Requirements Specification.
- Functional requirements.
- Non-functional requirements.
- User role matrix.
- Database relationship diagram.
- System architecture diagram.
- Initial UI navigation structure.

## Completion Criteria

All major requirements, user permissions and system relationships must be documented and approved before implementation.

---

# PHASE 1 – DEVELOPMENT ENVIRONMENT SETUP

## Objective

Prepare the laboratory workstation for Prism Desk development.

## 1.1 Operating System

Current development environment:

- Ubuntu 25.10.
- Python 3.13.7.
- AMD Ryzen 7 7735HS.
- 14 GB RAM.
- Approximately 178 GB available storage.

## 1.2 Backend Installation

Install:

- Python.
- Python virtual environment.
- FastAPI.
- Uvicorn.
- SQLAlchemy.
- Psycopg.
- Alembic.
- Pydantic.
- Pydantic Settings.

## 1.3 Database Installation

Install PostgreSQL.

Create:

Database name: prism_desk

Database user: prism_user

Default port: 5432.

## 1.4 Frontend Installation

Install:

- Node.js LTS.
- npm.
- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- shadcn/ui.

## 1.5 Development Tools

Install:

- Git.
- Docker Engine.
- Docker Compose.
- VS Code or preferred code editor.
- API testing tools where required.

## 1.6 Environment Verification

Verify:

- FastAPI starts.
- PostgreSQL starts.
- Database accepts connections.
- SQLAlchemy connects to PostgreSQL.
- React application starts.
- Frontend communicates with backend.
- Docker containers work.

## Deliverables

A fully functioning development environment.

## Completion Criteria

Every component passes its individual verification test.

---

# PHASE 2 – BACKEND FOUNDATION AND DATABASE DESIGN

## Objective

Create the database structure and backend foundation.

## 2.1 Backend Architecture

Organize FastAPI into modular components.

Recommended structure:

```text
backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── middleware/
│   └── main.py
│
├── tests/
├── alembic/
├── requirements.txt
├── alembic.ini
└── .env
```

## 2.2 Database Tables

Create the initial database schema.

| Table | Purpose |
|---|---|
| users | User accounts |
| roles | User roles |
| projects | Research projects |
| project_members | Project membership |
| research_papers | Research paper metadata |
| paper_notes | Student research notes |
| tasks | Assigned tasks |
| task_assignees | Task assignment relationships |
| task_submissions | Student submissions |
| handbook_entries | Daily research entries |
| handbook_comments | Professor feedback |
| discussions | Discussion threads |
| messages | Discussion replies |
| notifications | User notifications |
| audit_logs | Important system activities |

Additional tables may be introduced for individual messaging, reading lists and integrations.

## 2.3 Database Relationships

Important relationships:

```text
USERS
  |
  +---- PROJECT_MEMBERS ---- PROJECTS
  |
  +---- TASK_ASSIGNEES ----- TASKS
  |
  +---- HANDBOOK_ENTRIES
  |
  +---- RESEARCH_PAPERS
  |
  +---- NOTIFICATIONS
```

## 2.4 ORM

Use SQLAlchemy for database interactions.

## 2.5 Database Migration

Use Alembic.

Every database structure change should be tracked through migrations.

## 2.6 API Foundation

Create standard API modules:

- Authentication API.
- User API.
- Project API.
- Research API.
- Task API.
- Handbook API.
- Discussion API.
- Notification API.

## Deliverables

- Database schema.
- SQLAlchemy models.
- Database migrations.
- Backend API structure.
- Database connection configuration.
- Basic CRUD operations.

## Completion Criteria

FastAPI must successfully create, read, update and delete test records in PostgreSQL.

---

# PHASE 3 – AUTHENTICATION AND USER MANAGEMENT

## Objective

Develop the login system and user management functionality.

## 3.1 Authentication

Users log in using:

- Email address.
- Password.

The application should use secure session cookies.

Security requirements:

- Password hashing using a suitable password hashing algorithm.
- Secure cookie configuration.
- Session expiration.
- Session invalidation on logout.
- Login rate limiting.
- Password reset functionality.

## 3.2 Account Creation

Initially, public registration should be disabled.

Administrators can create accounts for:

- Professors.
- Students.
- Other authorized members.

An invitation-based registration workflow can be introduced later.

## 3.3 Role-Based Access Control

Implement RBAC.

Roles:

- Administrator.
- Professor.
- Student.

Permissions must be checked on the backend, not just hidden in the frontend.

## 3.4 User Profile

Each user should have:

- Full name.
- Email address.
- Profile picture (optional).
- Role.
- Department.
- Registration number (optional).
- Joining date.
- Account status.
- Research interests (optional).

## Deliverables

- Login.
- Logout.
- Session management.
- Account management.
- Role permissions.
- User profiles.
- Password reset.

## Completion Criteria

Each user can authenticate and access only authorized resources.

---

# PHASE 4 – RESEARCH PROJECT MANAGEMENT

## Objective

Develop a centralized project management system.

## 4.1 Project Creation

Professors and authorized administrators can create projects.

Project information:

- Project title.
- Description.
- Research domain.
- Research objectives.
- Creation date.
- Project status.
- Start date.
- Expected completion date.
- Assigned supervisors.
- Project members.

## 4.2 Project Membership

A student can belong to multiple projects.

A project can contain multiple students.

A project can have multiple professors.

Membership should support:

- Active.
- Inactive.
- Completed.

## 4.3 Project Dashboard

Each project should have its own workspace.

The workspace should include:

- Project overview.
- Supervisors.
- Members.
- Research papers.
- Tasks.
- Discussions.
- Announcements.
- Milestones.
- Recent activity.

## 4.4 Project Management Permissions

Professors should be able to:

- Add members.
- Remove members.
- Assign supervisors.
- Edit project details.
- Archive projects.

Students should only have access to assigned projects.

## Deliverables

- Project creation.
- Project editing.
- Membership management.
- Supervisor assignment.
- Project dashboard.
- Project archiving.

## Completion Criteria

The application must support multiple professors, projects and students with many-to-many relationships.

---

# PHASE 5 – RESEARCH PAPER AND RESOURCE MANAGEMENT

## Objective

Develop a shared research library.

## 5.1 Research Paper Entry

Users can add research papers using:

- Title.
- Authors.
- DOI.
- Publication.
- Journal or conference.
- Publication year.
- Paper URL.
- Abstract.
- Description.
- Associated project.
- Visibility.

## 5.2 Paper Sources

Support links from:

- IEEE Xplore.
- Springer.
- ACM Digital Library.
- arXiv.
- ScienceDirect.
- Google Scholar.
- ResearchGate.
- Other research websites.

The system should store links rather than downloading PDFs.

## 5.3 Reading Tracker

Each student can maintain their own reading status.

Statuses:

1. To Read.
2. Currently Reading.
3. Completed.
4. Need Discussion.

Reading status should be user-specific because multiple students may read the same paper independently.

## 5.4 Paper Notes

Students can write:

- Research summary.
- Methodology.
- Main findings.
- Limitations.
- Research gaps.
- Personal observations.

## 5.5 Paper Discussions

Users can comment on a paper.

Professors can respond to student observations.

## 5.6 Resource Library

Apart from research papers, users can share:

- GitHub repositories.
- Dataset websites.
- Tutorials.
- Documentation.
- Research tools.
- Conference websites.

## 5.7 Storage Management

Do not store paper PDFs.

Store only metadata, links, notes and discussions.

## Deliverables

- Research paper library.
- Resource sharing.
- Paper reading tracker.
- Paper notes.
- Paper discussions.
- Project-wise filtering.

## Completion Criteria

Students and professors can share, organize and discuss research resources.

---

# PHASE 6 – TASK MANAGEMENT AND ASSIGNMENT SYSTEM

## Objective

Allow professors to assign research tasks and monitor student progress.

## 6.1 Task Creation

A professor can create a task containing:

- Task title.
- Description.
- Project.
- Assigned students.
- Priority.
- Deadline.
- Instructions.
- Reference papers.
- Expected deliverables.

## 6.2 Task Status

Use the following workflow:

```text
ASSIGNED
    |
    v
IN PROGRESS
    |
    v
SUBMITTED
    |
    v
UNDER REVIEW
    |
    +------ APPROVED
    |
    +------ REVISION REQUIRED
                 |
                 v
             IN PROGRESS
```

Completed tasks should retain their submission and review history.

## 6.3 Student Functionality

Students can:

- View tasks.
- Acknowledge assignments.
- Update progress.
- Submit completed work.
- Add comments.
- Ask questions.
- Request deadline extensions.

## 6.4 Professor Functionality

Professors can:

- Assign tasks.
- Assign tasks to multiple students.
- Set deadlines.
- Review submissions.
- Provide feedback.
- Approve submissions.
- Request revisions.
- Track overdue tasks.

## 6.5 Task Notifications

Generate notifications for:

- New task assignments.
- Approaching deadlines.
- Overdue tasks.
- New feedback.
- Submission approvals.
- Revision requests.

## Deliverables

- Task creation.
- Task assignment.
- Task status tracking.
- Submission workflow.
- Professor review.
- Task history.
- Notifications.

## Completion Criteria

A professor can assign tasks, and students can submit them for review.

---

# PHASE 7 – DAILY RESEARCH HANDBOOK

## Objective

Develop a digital research diary for every student.

This is one of the core features of Prism Desk.

## 7.1 Handbook Structure

Each entry should contain:

- Date.
- Student.
- Project.
- Today's activities.
- Research papers studied.
- Work completed.
- Problems encountered.
- Tomorrow's plan.
- Time spent (optional).
- References.

## 7.2 Project-Wise Entries

Recommended design:

Students should maintain separate daily entries for each project.

An optional overall daily summary can combine their activities across projects.

## 7.3 Student Functionality

Students can:

- Create entries.
- Edit previous entries.
- View handbook history.
- Search entries.
- Filter by project.
- Link research papers.
- Maintain daily records.

## 7.4 Professor Functionality

Professors can:

- View assigned students' entries.
- Filter by student.
- Filter by project.
- Add comments.
- Provide feedback.
- Review historical entries.

## 7.5 Handbook Edit History

Maintain a record of important edits.

This should include:

- Original entry.
- Updated entry.
- Updated timestamp.
- User responsible for the modification.

## 7.6 Weekly Reports

Generate summaries containing:

- Number of entries.
- Activities performed.
- Papers studied.
- Tasks completed.
- Problems encountered.
- Pending activities.

## 7.7 Monthly Reports

Generate project-wise and student-wise research summaries.

## Deliverables

- Digital handbook.
- Date-wise history.
- Project-wise filtering.
- Professor review.
- Handbook comments.
- Weekly and monthly reports.

## Completion Criteria

Students can maintain daily research records and professors can review them.

---

# PHASE 8 – COMMUNICATION AND DISCUSSION SYSTEM

## Objective

Provide research-oriented communication inside Prism Desk.

## 8.1 Project Discussions

Every project should have a dedicated discussion area.

Members can:

- Create discussion threads.
- Reply to discussions.
- Share links.
- Ask questions.
- Discuss research findings.

## 8.2 Individual Communication

Support private professor-student communication.

Messages should include:

- Sender.
- Receiver.
- Message.
- Timestamp.
- Read status.

## 8.3 Task Discussions

Each task should support comments and replies.

## 8.4 Paper Discussions

Each research paper should support comments and replies.

## 8.5 Announcements

Professors can publish announcements for:

- Entire laboratory.
- Selected projects.
- Selected students.

## 8.6 Notification System

Users should receive notifications when:

- They receive a message.
- A professor comments on their work.
- A discussion receives a reply.
- An announcement is published.
- A task is assigned.

## Deliverables

- Project discussions.
- Individual messages.
- Task comments.
- Paper discussions.
- Announcements.
- Notification system.

## Completion Criteria

Communication works according to user permissions and remains connected to relevant research activities.

---

# PHASE 9 – DISCORD INTEGRATION

## Objective

Integrate Discord with Prism Desk for communication and notifications.

Discord will complement Prism Desk rather than replace it.

## 9.1 Discord Server

Create a private PRISM laboratory Discord server.

Suggested structure:

```text
PRISM LAB
│
├── GENERAL
│   ├── announcements
│   ├── general-chat
│   └── lab-updates
│
├── PROJECTS
│   ├── project-causalshield
│   ├── project-cache-sentry
│   └── project-other
│
├── RESEARCH
│   ├── paper-discussions
│   └── useful-resources
│
└── VOICE
    ├── lab-meeting
    └── research-room
```

## 9.2 Webhook Integration

Initially, use Discord webhooks.

Events that can trigger notifications:

- New task assignment.
- New announcement.
- Task deadline reminder.
- Submission received.
- Professor feedback.
- New research paper.
- Important project updates.

## 9.3 Notification Routing

Project notifications should be sent to the appropriate project channel.

Private student information should not be posted to public project channels.

## 9.4 Discord Bot

A dedicated bot can be developed later.

Possible commands:

- /mytasks
- /myprojects
- /deadline
- /progress
- /handbook

The bot must verify the user's Prism Desk account before providing private information.

## Deliverables

- Discord server integration.
- Webhook configuration.
- Project-specific notifications.
- Optional Discord bot.

## Completion Criteria

Prism Desk can send notifications to Discord without making Discord a dependency for core application functionality.

---

# PHASE 10 – DASHBOARDS AND RESEARCH ANALYTICS

## Objective

Provide separate dashboards for administrators, professors and students.

## 10.1 Administrator Dashboard

Display:

- Total users.
- Total professors.
- Total students.
- Active projects.
- Archived projects.
- Recent system activities.
- User account status.

## 10.2 Professor Dashboard

Display:

- Assigned students.
- Active projects.
- Pending tasks.
- Overdue tasks.
- Submissions awaiting review.
- Recent handbook entries.
- Recent research papers.
- Upcoming deadlines.

## 10.3 Student Dashboard

Display:

- My projects.
- Pending tasks.
- Upcoming deadlines.
- Recently shared papers.
- Handbook shortcut.
- Professor feedback.
- Notifications.

## 10.4 Project Dashboard

Display:

- Project information.
- Supervisors.
- Members.
- Research papers.
- Tasks.
- Discussions.
- Milestones.
- Recent activity.

## 10.5 Research Analytics

Possible metrics:

- Tasks completed per student.
- Weekly handbook activity.
- Project-wise progress.
- Papers added.
- Papers marked completed.
- Overdue tasks.
- Project milestone completion.

These metrics should support supervision rather than automatically judge research quality.

## Deliverables

- Administrator dashboard.
- Professor dashboard.
- Student dashboard.
- Project dashboard.
- Research analytics.

## Completion Criteria

Each role receives a dashboard containing relevant and permission-controlled information.

---

# PHASE 11 – TESTING, SECURITY AND QUALITY ASSURANCE

## Objective

Verify the correctness, security and reliability of Prism Desk.

## 11.1 Backend Testing

Use Pytest.

Test:

- Authentication.
- Authorization.
- User management.
- Project management.
- Research paper management.
- Task assignment.
- Task submissions.
- Handbook operations.
- Discussions.
- Notifications.
- Discord integration.

## 11.2 Frontend Testing

Test:

- Login.
- Navigation.
- Forms.
- Dashboard loading.
- Project switching.
- Paper sharing.
- Task submission.
- Handbook editing.
- Responsive layouts.

## 11.3 Security Testing

Verify:

- Password hashing.
- Session security.
- Role-based permissions.
- Unauthorized access prevention.
- SQL injection protection.
- Input validation.
- CSRF protection where applicable.
- Rate limiting.
- Environment variable protection.
- Audit logging.

## 11.4 Multi-User Testing

Simulate multiple users operating simultaneously.

Example:

- Professor assigns a task.
- Student 1 updates a handbook.
- Student 2 submits an assignment.
- Student 3 shares a paper.
- Administrator checks project activity.

Verify that the application handles concurrent operations correctly.

## 11.5 Backup Testing

Implement:

- Automatic database backup.
- Backup retention.
- Restoration testing.
- Recovery procedures.

## Deliverables

- Automated test suite.
- Security testing report.
- Performance testing report.
- Backup and recovery procedure.
- Bug-fixing report.

## Completion Criteria

All critical tests pass, and no unresolved critical security issues remain.

---

# PHASE 12 – WORKSTATION DEPLOYMENT

## Objective

Deploy Prism Desk on the PRISM laboratory workstation.

## 12.1 Server Configuration

The workstation will host:

- React frontend.
- FastAPI backend.
- PostgreSQL database.
- Nginx.
- Docker Compose deployment.

## 12.2 Deployment Architecture

```text
          PRISM WORKSTATION
                  |
          +-------+-------+
          |               |
         NGINX        POSTGRESQL
          |
        FASTAPI
          |
      REACT BUILD
          |
      LAB NETWORK
          |
     +----+----+
     |    |    |
   ADMIN PROF STUDENTS
```

## 12.3 Network Configuration

Configure:

- Stable local IP.
- Appropriate firewall rules.
- Authorized user access.
- Local hostname if required.
- HTTPS where appropriate.

## 12.4 Automatic Startup

The application should restart automatically after workstation reboot.

Use appropriate service management and Docker restart policies.

## 12.5 Monitoring

Monitor:

- CPU usage.
- RAM usage.
- Disk usage.
- PostgreSQL health.
- Application availability.
- Error logs.
- Backup status.

## 12.6 Backup Strategy

Database backups should be stored separately from the primary database location.

Where possible, maintain an additional backup on another device or external storage.

## Deliverables

- Production deployment.
- Network accessibility.
- Backup automation.
- Monitoring.
- User documentation.

## Completion Criteria

Authorized laboratory users can access Prism Desk reliably through the local network.

---

# PHASE 13 – ADVANCED FEATURES AND FUTURE DEVELOPMENT

## Objective

Introduce advanced capabilities after the initial application is stable.

These features are not required for the first release.

## 13.1 AI Research Assistant

Possible capabilities:

- Research paper summarization.
- Research gap identification assistance.
- Literature comparison.
- Research question answering.
- Research note summarization.

AI should only use documents and information that the requesting user is authorized to access.

## 13.2 AI Handbook Assistant

Possible capabilities:

- Weekly activity summaries.
- Monthly research summaries.
- Progress report generation.
- Identification of recurring problems.
- Research activity summaries.

## 13.3 Semantic Research Search

Allow users to search using natural language.

Example:

"Find papers related to cyber-physical intrusion detection using attention-based feature fusion."

The system can retrieve relevant papers from the laboratory's stored metadata and notes.

## 13.4 GitHub Integration

Allow students to connect research repositories.

Possible features:

- Repository links.
- Commit activity.
- Project repository listing.
- Research implementation tracking.

## 13.5 Meeting Scheduler

Allow professors to:

- Schedule meetings.
- Invite students.
- Define meeting agendas.
- Record meeting notes.
- Track follow-up tasks.

## 13.6 Advanced Analytics

Introduce:

- Project milestone analytics.
- Research activity trends.
- Task completion analysis.
- Historical progress reports.

## 13.7 Discord Bot

Allow authenticated students to retrieve selected Prism Desk information through Discord.

## 13.8 Report Export

Support exporting:

- Daily handbooks.
- Weekly reports.
- Monthly reports.
- Project progress reports.
- Research paper lists.

Formats:

- PDF.
- Excel.
- CSV.

## Deliverables

Advanced research collaboration and automation capabilities.

## Completion Criteria

Advanced features must integrate with the existing architecture without compromising security or the stability of core modules.

---

# 20. DATABASE DESIGN OVERVIEW

The database will use PostgreSQL.

The initial schema should contain the following logical groups.

## 20.1 User Management

- users
- roles
- user_sessions

## 20.2 Project Management

- projects
- project_members
- project_supervisors
- project_milestones

## 20.3 Research Management

- research_papers
- paper_project_links
- paper_reading_status
- paper_notes
- paper_comments
- shared_resources

## 20.4 Task Management

- tasks
- task_assignees
- task_submissions
- task_comments
- task_status_history

## 20.5 Handbook

- handbook_entries
- handbook_comments
- handbook_edit_history

## 20.6 Communication

- discussions
- messages
- message_read_status
- announcements

## 20.7 Notifications

- notifications
- notification_preferences

## 20.8 Integration

- discord_integrations
- discord_channel_mappings
- discord_notification_logs

## 20.9 System Management

- audit_logs
- application_settings

The final schema should be reviewed and normalized before implementation.

All tables should use suitable primary keys, foreign keys, unique constraints and indexes.

---

# 21. SECURITY REQUIREMENTS

Security must be considered throughout development.

## Authentication

- Secure password hashing.
- Session management.
- Session expiration.
- Secure cookies.
- Login rate limiting.

## Authorization

- Role-based access control.
- Project membership checks.
- Professor-student relationship checks.
- Handbook visibility checks.
- Task ownership checks.

## Database

- Dedicated database user.
- Restricted database permissions.
- Parameterized queries through SQLAlchemy.
- Database credentials stored outside source code.
- Regular backups.

## Network

- PostgreSQL should not be publicly exposed.
- Firewall should restrict unnecessary access.
- HTTPS should be used where appropriate.
- Administrative interfaces should have restricted access.

## Application

- Validate user inputs.
- Protect against CSRF and XSS.
- Avoid exposing internal error messages.
- Maintain security audit logs.
- Protect Discord webhook secrets.

---

# 22. STORAGE MANAGEMENT STRATEGY

The workstation has limited storage, so Prism Desk should minimize file storage.

## 22.1 Research Papers

Do not store research paper PDFs.

Store:

- Paper title.
- Authors.
- DOI.
- Publication.
- Paper URL.
- Abstract.
- Notes.
- Discussions.

## 22.2 Handbook

Store daily handbook text in PostgreSQL.

## 22.3 Messages

Store messages and discussion text in PostgreSQL.

## 22.4 Attachments

For the initial version, avoid arbitrary file uploads.

If attachments become necessary, use a separately configured storage directory with file-size limits and storage monitoring.

## 22.5 Database Backups

Backups must be stored separately from the active database.

A suggested starting policy:

- Daily backups.
- Seven daily backup copies.
- Four weekly backup copies.
- One monthly backup copy.

Actual retention should be adjusted to available storage.

---

# 23. CODEX DEVELOPMENT WORKFLOW

Codex will be used for implementation.

However, development must proceed phase by phase.

## 23.1 Development Process

```text
       PHASE REQUIREMENTS
               |
               v
       CODEX INSTRUCTIONS
               |
               v
       CODE IMPLEMENTATION
               |
               v
         CODE REVIEW
               |
               v
        LOCAL TESTING
               |
               v
          BUG FIXING
               |
               v
      ACCEPTANCE TESTING
               |
               v
          GIT COMMIT
               |
               v
        NEXT PHASE
```

## 23.2 Instructions for Codex

For every phase, provide:

1. Objective.
2. Scope.
3. Existing architecture.
4. Database requirements.
5. API requirements.
6. Frontend requirements.
7. Permission requirements.
8. Security requirements.
9. Testing requirements.
10. Acceptance criteria.

## 23.3 Important Development Rules

- Do not implement unrelated features.
- Do not rewrite working modules unnecessarily.
- Follow the established folder structure.
- Use Alembic migrations.
- Do not store secrets in source code.
- Implement backend authorization.
- Add tests for new features.
- Maintain API documentation.
- Update project documentation.
- Run regression tests after modifications.

## 23.4 Git Strategy

Maintain Git commits after completing each verified phase.

Suggested branch structure:

- main
- development
- feature/authentication
- feature/projects
- feature/research-library
- feature/tasks
- feature/handbook
- feature/discord-integration

Merge tested features into the development branch and release stable versions through main.

---

# 24. FINAL PROJECT DELIVERABLES

At the end of development, Prism Desk should contain the following modules.

| Module | Final Deliverable |
|---|---|
| Authentication | Secure login and account management |
| User Management | Administrator, professor and student accounts |
| Project Management | Multi-project and multi-supervisor support |
| Research Library | Paper and resource sharing |
| Reading Tracker | Paper reading status |
| Task Management | Assignments and submissions |
| Daily Handbook | Digital research diary |
| Professor Review | Handbook and submission feedback |
| Discussions | Project and research discussions |
| Communication | Individual messages |
| Discord Integration | Notifications and optional bot |
| Dashboards | Role-specific dashboards |
| Analytics | Research progress reports |
| Database | Local PostgreSQL |
| Security | RBAC and audit logging |
| Deployment | Laboratory workstation hosting |
| Backup | Automated backup and recovery |

---

# 25. DEVELOPMENT ROADMAP AND COMPLETION CRITERIA

| Phase | Name | Priority |
|---|---|---|
| 0 | Requirement Analysis | Critical |
| 1 | Development Environment | Critical |
| 2 | Backend and Database | Critical |
| 3 | Authentication | Critical |
| 4 | Project Management | Critical |
| 5 | Research Library | High |
| 6 | Task Management | Critical |
| 7 | Daily Handbook | Critical |
| 8 | Communication | High |
| 9 | Discord Integration | Medium |
| 10 | Dashboards and Analytics | High |
| 11 | Testing and Security | Critical |
| 12 | Workstation Deployment | Critical |
| 13 | Advanced Features | Future |

## FIRST RELEASE – PRISM DESK V1

The first production release should include:

- Administrator login.
- Professor login.
- Student login.
- Multiple professor support.
- Project management.
- Research paper sharing.
- Paper reading tracker.
- Task assignments.
- Task submissions.
- Daily research handbook.
- Professor handbook review.
- Project discussions.
- Notifications.
- Basic Discord webhooks.
- Role-specific dashboards.
- Local PostgreSQL database.
- Workstation deployment.

## SECOND RELEASE – PRISM DESK V2

- Private messaging.
- Advanced Discord integration.
- Weekly and monthly reports.
- Advanced analytics.
- Meeting scheduling.
- Improved notification preferences.

## THIRD RELEASE – PRISM DESK V3

- AI research assistant.
- Semantic research search.
- Automatic progress summaries.
- GitHub integration.
- Discord bot.
- Advanced research analytics.

---

# CONCLUSION

Prism Desk is intended to become the central digital workspace of the PRISM laboratory.

The platform will connect professors, students and research projects through a common system for research paper management, task assignments, daily handbooks, discussions and progress monitoring.

The system will use a self-hosted PostgreSQL database and will be deployed on the laboratory workstation.

Discord will provide an additional communication channel without becoming a dependency for the core application.

The development process will follow a phase-wise approach. Each phase must be implemented, tested, documented and verified before proceeding to the next phase.

The initial objective is to build a reliable and secure laboratory management platform. Advanced AI and automation features will be introduced only after the core system is stable.

**PRISM DESK**

*One Lab. Multiple Projects. Connected Research.*