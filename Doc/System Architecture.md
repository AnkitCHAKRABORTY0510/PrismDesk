# PRISM DESK
## System Architecture Document

**Project:** Prism Desk  
**Laboratory:** PRISM Laboratory  
**Document:** System Architecture Specification  
**Version:** 1.0  
**Phase:** Phase 0 – Requirements Analysis and System Design  
**Status:** Initial Architecture Baseline

---

# 1. Introduction

## 1.1 Purpose

This document describes the overall technical architecture of Prism Desk.

It defines:

- Frontend architecture.
- Backend architecture.
- Database architecture.
- Discord integration.
- Authentication and authorisation.
- API communication.
- Application deployment.
- Network architecture.
- Security boundaries.
- Backup and recovery architecture.

The objective is to establish a maintainable architecture that supports the current laboratory requirements and future expansion.

## 1.2 System Overview

Prism Desk is a self-hosted, browser-based laboratory management and research collaboration application.

The application will run on a dedicated laboratory workstation.

Laboratory members will access it through their web browsers using the laboratory network.

The system will use:

- React and TypeScript for the frontend.
- Python and FastAPI for the backend.
- PostgreSQL for database storage.
- Discord for communication and notifications.
- Docker for application deployment.
- Nginx as a reverse proxy.

## 1.3 Architectural Approach

Prism Desk will use a **Modular Monolithic Architecture**.

The application will have one main backend application, divided into independent functional modules.

It will not use microservices in the initial version.

### Why a Modular Monolith?

The laboratory initially has approximately 30 users.

A microservices architecture would introduce unnecessary complexity, including:

- Multiple backend services.
- Inter-service communication.
- Distributed authentication.
- More deployment components.
- More complicated debugging.
- Additional resource consumption.

A modular monolith provides sufficient separation between application modules without introducing these overheads.

---

# 2. High-Level System Architecture

The system will contain five primary components:

1. Presentation Layer.
2. Application Layer.
3. Database Layer.
4. External Integration Layer.
5. Deployment and Infrastructure Layer.

## 2.1 Architecture Diagram

```text
                  PRISM LABORATORY
                         |
             -------------------------
             |           |           |
          Student     Professor   Administrator
             |           |           |
             -------------------------
                         |
                    Web Browser
                         |
                         |
                  NGINX REVERSE
                      PROXY
                         |
                         |
                  REACT FRONTEND
                  + TYPESCRIPT
                         |
                    HTTP / REST
                         |
                         |
                   FASTAPI BACKEND
                         |
        -------------------------------------
        |          |           |            |
        |          |           |            |
      AUTH     PROJECT       TASK       RESEARCH
      MODULE   MODULE        MODULE     LIBRARY
        |          |           |            |
        -------------------------------------
                         |
        -------------------------------------
        |          |           |            |
        |          |           |            |
     HANDBOOK  CONFERENCE  NOTIFICATION   AUDIT
      MODULE    MODULE       MODULE       MODULE
        |          |           |            |
        -------------------------------------
                         |
                 SQLALCHEMY ORM
                         |
                         |
                    POSTGRESQL
                         |
                  LOCAL DATABASE
                         |
                  LAB WORKSTATION


                 EXTERNAL INTEGRATION
                         |
                      DISCORD
                         |
             -------------------------
             |                       |
        Communication            Notifications
```

The frontend communicates with the backend through REST APIs.

The backend communicates with PostgreSQL through SQLAlchemy.

Discord is accessed through the backend integration module.

---

# 3. Frontend Architecture

## 3.1 Technology

The frontend will use:

| Technology | Purpose |
|---|---|
| React | User interface |
| TypeScript | Type-safe development |
| Vite | Development server and build system |
| Tailwind CSS | Styling |
| shadcn/ui | Reusable UI components |
| React Router | Application navigation |
| TanStack Query | API data fetching and caching |
| React Hook Form | Form management |
| Zod | Frontend validation |

These libraries will form the initial frontend stack.

## 3.2 Frontend Responsibilities

The frontend will handle:

- User registration.
- Login and logout.
- Dashboard display.
- Project management interfaces.
- Research paper management.
- Task management.
- Daily research handbook.
- Conference deadline tracking.
- User management.
- Guest permission interfaces.
- Notification preferences.
- Activity history.

The frontend must not directly connect to PostgreSQL.

All database operations must pass through the backend API.

## 3.3 Frontend Module Structure

The frontend should be organised into functional modules.

```text
frontend/
|
├── src/
│   |
│   ├── components/
│   |   ├── common/
│   |   ├── layout/
│   |   ├── forms/
│   |   └── ui/
│   |
│   ├── pages/
│   |   ├── auth/
│   |   ├── dashboard/
│   |   ├── projects/
│   |   ├── research-library/
│   |   ├── tasks/
│   |   ├── handbook/
│   |   ├── conferences/
│   |   ├── users/
│   |   ├── guests/
│   |   └── settings/
│   |
│   ├── features/
│   |   ├── authentication/
│   |   ├── project-management/
│   |   ├── research-management/
│   |   ├── task-management/
│   |   ├── handbook-management/
│   |   ├── discord-integration/
│   |   ├── notifications/
│   |   └── analytics/
│   |
│   ├── hooks/
│   ├── services/
│   ├── contexts/
│   ├── types/
│   ├── utils/
│   |
│   ├── App.tsx
│   └── main.tsx
|
└── package.json
```

The frontend should use reusable components wherever possible.

## 3.4 Role-Based Interface

The application interface should adapt according to the authenticated user's permissions.

For example:

**Administrator**
- User management.
- Registration approvals.
- Laboratory dashboard.
- Project administration.
- Deleted projects.
- System settings.

**Professor**
- Supervised projects.
- Student monitoring.
- Task assignment.
- Handbook review.
- Research library.

**Student**
- My projects.
- Assigned tasks.
- Personal tasks.
- Research handbook.
- Research library.

**Guest**
- Only administrator-authorised sections.

Frontend visibility is for usability. Actual access restrictions must always be enforced by the backend.

---

# 4. Backend Architecture

## 4.1 Technology

The backend will use:

| Technology | Purpose |
|---|---|
| Python | Programming language |
| FastAPI | Backend framework |
| Uvicorn | ASGI application server |
| SQLAlchemy | Database ORM |
| Alembic | Database migrations |
| Pydantic | Data validation |
| Psycopg | PostgreSQL connectivity |
| Pytest | Backend testing |

## 4.2 Backend Responsibilities

The backend will manage:

1. Authentication.
2. User management.
3. Role and permission enforcement.
4. Project management.
5. Project membership.
6. Research paper management.
7. Task management.
8. Task submissions.
9. Daily research handbooks.
10. Handbook comments.
11. Conference deadlines.
12. Discord integration.
13. Notification preferences.
14. Activity logging.
15. Database operations.

## 4.3 Backend Module Structure

```text
backend/
|
├── app/
│   |
│   ├── main.py
│   |
│   ├── core/
│   |   ├── config.py
│   |   ├── security.py
│   |   ├── permissions.py
│   |   └── logging.py
│   |
│   ├── database/
│   |   ├── session.py
│   |   ├── base.py
│   |   └── migrations/
│   |
│   ├── models/
│   |   ├── user.py
│   |   ├── role.py
│   |   ├── project.py
│   |   ├── task.py
│   |   ├── research_paper.py
│   |   ├── handbook.py
│   |   ├── conference.py
│   |   ├── notification.py
│   |   └── audit.py
│   |
│   ├── schemas/
│   |
│   ├── api/
│   |   └── v1/
│   |       ├── auth.py
│   |       ├── users.py
│   |       ├── projects.py
│   |       ├── research.py
│   |       ├── tasks.py
│   |       ├── handbook.py
│   |       ├── conferences.py
│   |       ├── notifications.py
│   |       └── discord.py
│   |
│   ├── services/
│   |   ├── auth_service.py
│   |   ├── project_service.py
│   |   ├── task_service.py
│   |   ├── research_service.py
│   |   ├── handbook_service.py
│   |   ├── discord_service.py
│   |   └── notification_service.py
│   |
│   ├── integrations/
│   |   └── discord/
│   |
│   └── tests/
|
├── alembic.ini
├── requirements.txt
└── venv/
```

This is the proposed target structure. The existing FastAPI test application can be reorganised into this structure during backend development.

## 4.4 Backend Layer Separation

Each module should separate:

**API Layer**

Receives HTTP requests and returns responses.

**Schema Layer**

Validates incoming and outgoing data.

**Service Layer**

Implements application business logic.

**Model Layer**

Defines database entities.

**Database Layer**

Handles database sessions and connections.

This separation will improve maintainability and testing.

---

# 5. Database Architecture

## 5.1 Database Technology

PostgreSQL will be the primary database.

It will run locally on the laboratory workstation.

The backend will connect to it using SQLAlchemy and Psycopg.

## 5.2 Database Responsibilities

PostgreSQL will store:

- User accounts.
- User roles.
- Registration requests.
- Project records.
- Project memberships.
- Research paper metadata.
- Research paper URLs.
- Paper-project associations.
- Student reading statuses.
- Personal research notes.
- Tasks.
- Task assignments.
- Task submissions.
- Handbook entries.
- Handbook comments and replies.
- Handbook edit history.
- Conference records.
- Notification preferences.
- Discord account mappings.
- Activity logs.
- Deleted project records or deletion metadata.

## 5.3 Database Organisation

Each project will maintain its own:

- Members.
- Tasks.
- Task assignments.
- Handbook entries.
- Project-specific discussions and records.
- Conference deadlines.

Research papers and selected resources can be shared across multiple projects.

A paper should have one central database record with separate project associations.

## 5.4 File Storage Policy

Prism Desk will not implement file uploads.

PostgreSQL will store only structured information and text.

The system will not store:

- PDFs.
- Images.
- Screenshots.
- Videos.
- Audio.
- Word documents.
- ZIP files.
- Research datasets.

Users can share screenshots and attachments through Discord, but Prism Desk will not download or copy them.

---

# 6. Authentication and Security Architecture

## 6.1 Authentication

Users can log in using:

- Username and password.
- Email and password.

New accounts require administrator approval.

## 6.2 Session Management

The backend should use secure, server-managed authentication sessions.

Recommended implementation:

- Random, unpredictable session identifiers.
- Session records stored server-side.
- Secure, HttpOnly cookies.
- SameSite cookie protection.
- HTTPS in production.
- Session expiration.
- Logout and session revocation.

The frontend should not store authentication secrets in localStorage.

## 6.3 Automatic Logout

The system should automatically terminate inactive sessions.

The inactivity duration will be configurable.

## 6.4 Role-Based Access Control

The backend will enforce role-based permissions.

The application should support:

- Administrator.
- Professor.
- Student.
- Guest.

Project-level membership will provide an additional access-control layer.

## 6.5 Security Boundaries

```text
             WEB BROWSER
                  |
                  |
             NGINX PROXY
                  |
                  |
             FASTAPI API
                  |
          -------------------
          |                 |
     AUTHENTICATION     AUTHORISATION
          |                 |
          -------------------
                  |
                  |
             SQLALCHEMY
                  |
                  |
              POSTGRESQL
```

The browser must never communicate directly with PostgreSQL.

Database credentials must remain on the server.

---

# 7. Discord Integration Architecture

## 7.1 Purpose

Discord will be the primary communication and notification platform.

Prism Desk will not implement a separate internal chat system in the initial release.

## 7.2 Integration Components

The backend will contain a dedicated Discord integration module.

It will be responsible for:

- Discord account linking.
- Discord server integration.
- Project-channel mapping.
- Sending notifications.
- Managing notification preferences.
- Validating user-to-Discord account associations.

## 7.3 Discord Communication Flow

```text
          USER ACTION
               |
               v
         PRISM DESK
               |
               v
        FASTAPI BACKEND
               |
               v
       DISCORD INTEGRATION
               |
               v
          DISCORD API
               |
               v
        PRISM DISCORD SERVER
```

Example:

1. Professor assigns a task.
2. FastAPI records the assignment in PostgreSQL.
3. Notification service checks the student's preferences.
4. Discord integration sends a notification.
5. Student receives the notification through Discord.

The database remains the source of truth for tasks, assignments and research records.

## 7.4 Discord Account Linking

Each user can connect their Prism Desk account to their Discord account.

The integration must prevent one Discord account from being incorrectly associated with multiple active Prism Desk users.

Account linking should use a secure verification process.

## 7.5 Notification Preferences

The backend will maintain per-user notification preferences.

Users can independently disable notification categories.

Notifications should be sent only when the relevant event is enabled.

## 7.6 Discord Failure Handling

If Discord becomes unavailable:

- Core Prism Desk functionality should continue working.
- Database records must still be saved.
- Failed notifications should be logged.
- Temporary notification failures should be retried where appropriate.

Discord availability must not determine whether a task or handbook entry is successfully saved.

---

# 8. API Architecture

## 8.1 API Communication

The React frontend will communicate with FastAPI through REST APIs.

Data will be exchanged using JSON.

## 8.2 API Versioning

All application endpoints should use versioned routes.

Base path:

```text
/api/v1/
```

## 8.3 Proposed API Modules

| API Module | Purpose |
|---|---|
| /auth | Registration, login, logout and password reset |
| /users | User management |
| /roles | Role management |
| /projects | Project management |
| /members | Project membership |
| /research | Research paper management |
| /tasks | Task management |
| /submissions | Task submissions |
| /handbook | Daily research handbook |
| /comments | Handbook comments and replies |
| /conferences | Conference deadline tracking |
| /notifications | Notification preferences |
| /discord | Discord account linking and integration |
| /dashboard | Role-specific dashboards |
| /audit | Activity and audit history |

These are proposed API groups, not final endpoint definitions.

Detailed endpoints will be designed during backend implementation.

## 8.4 API Documentation

FastAPI will provide automatic API documentation.

The development environment will use:

```text
/docs
```

for Swagger UI and:

```text
/redoc
```

for ReDoc.

---

# 9. Deployment Architecture

## 9.1 Hosting Environment

Prism Desk will initially run on the laboratory workstation.

The workstation will host:

- React frontend build.
- FastAPI backend.
- PostgreSQL database.
- Nginx.
- Docker containers.

## 9.2 Deployment Diagram

```text
             LAB WORKSTATION
             UBUNTU LINUX
                    |
        -------------------------
        |           |           |
      NGINX       FASTAPI    POSTGRESQL
        |           |           |
        |           |           |
     FRONTEND    BACKEND     DATABASE
        |           |
        ------------- 
              |
          LOCAL LAN
              |
       ----------------
       |       |      |
     PC-1    PC-2   Laptop
       |       |      |
       ----------------
              |
          WEB BROWSER
```

Laboratory members will access the application through the workstation's LAN address or a local DNS hostname.

## 9.3 Docker Architecture

Docker Compose will manage the application containers.

Proposed services:

1. frontend
2. backend
3. database
4. nginx

PostgreSQL should not be exposed directly to the laboratory network.

Only the backend should connect to the database.

## 9.4 Network Security

Initial deployment should be LAN-only.

Requirements:

- Restrict application access to the laboratory network.
- Do not expose PostgreSQL publicly.
- Use firewall rules.
- Keep database credentials private.
- Protect administrative endpoints.
- Do not expose development servers to the public internet.

HTTPS should be configured for production access, including internal network access where practical.

---

# 10. Backup and Recovery Architecture

## 10.1 Backup Strategy

PostgreSQL data will be backed up automatically every day.

Initially, backup files will be stored on the same laboratory workstation.

## 10.2 Backup Contents

Backups should include:

- User records.
- Projects.
- Project memberships.
- Research paper metadata.
- Tasks.
- Submissions.
- Handbook entries.
- Comments and replies.
- Conference records.
- Notification preferences.
- Discord account mappings.
- Audit history.

Discord attachments are not included because Prism Desk does not store them.

## 10.3 Recovery

The system should support restoring the PostgreSQL database from a valid backup.

Backup restoration must be tested before production deployment.

## 10.4 Future Improvement

An external backup location should be added later.

Keeping all backups on the same workstation does not protect against workstation failure, theft or disk damage.

---

# 11. Monitoring and Logging Architecture

The system should maintain two types of logs.

## 11.1 Application Logs

These record:

- Backend errors.
- API failures.
- Database connection problems.
- Discord integration errors.
- Authentication failures.
- Unexpected application behaviour.

## 11.2 Audit Logs

These record important user activities.

Examples:

- Project creation.
- Task updates.
- Paper additions.
- Handbook edits.
- Account approvals.
- Membership changes.
- Project deletion.

Application logs and audit logs should be maintained separately.

Sensitive information, passwords and authentication tokens must never be written to logs.

---

# 12. Scalability and Future Expansion

The initial architecture will support approximately 30 laboratory users.

The modular design should allow future addition of:

- More professors.
- More students.
- Additional projects.
- Research analytics.
- AI-based research assistance.
- Semantic paper search.
- Automated research summaries.
- GitHub integration.
- Advanced Discord bot commands.
- Meeting scheduling.
- Additional laboratory modules.

These features should be added without requiring a complete architectural redesign.

---

# 13. Architecture Design Principles

The following principles must guide implementation.

1. Use a modular monolithic backend.
2. Maintain clear frontend and backend separation.
3. Never allow direct frontend-to-database communication.
4. Use PostgreSQL as the central source of truth.
5. Enforce permissions in the backend.
6. Keep personal research notes private.
7. Maintain project-level access restrictions.
8. Keep Discord integration independent of core application functionality.
9. Do not implement file-upload or attachment-storage functionality.
10. Use database migrations for schema changes.
11. Maintain automated daily database backups.
12. Use environment variables for secrets and configuration.
13. Maintain application logs and audit logs separately.
14. Design modules for future expansion.

---

# 14. Architecture Acceptance Criteria

The architecture will be considered ready for implementation when:

- Frontend and backend communicate successfully.
- PostgreSQL connectivity is established.
- Backend modules have defined responsibilities.
- Authentication and permission enforcement are designed.
- Discord integration has a defined communication flow.
- Database access is restricted to the backend.
- LAN deployment architecture is established.
- Daily backup procedures are defined.
- No file-storage component is included.
- API versioning is established.
- The project can be deployed using the selected infrastructure.

---

# 15. Final Architecture Statement

Prism Desk will use a self-hosted modular monolithic architecture.

The frontend will be developed using React and TypeScript.

The backend will use Python and FastAPI.

PostgreSQL will serve as the primary database.

Discord will provide communication and notification capabilities.

Docker Compose and Nginx will support deployment on the PRISM laboratory workstation.

The architecture will prioritise maintainability, security, storage efficiency and future scalability.

**Document Status:** System Architecture Specification – Version 1.0.