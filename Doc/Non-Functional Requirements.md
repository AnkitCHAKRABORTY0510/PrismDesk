# PRISM DESK
## Non-Functional Requirements (NFR)
**Document:** 7 of Phase 0 — Requirements Analysis and System Design  
**Version:** 1.0  
**Application:** Prism Desk  
**Tagline:** One Lab. Multiple Projects. Connected Research.

---

# 1. Introduction

## 1.1 Purpose

This document defines the quality, performance, security, reliability, and operational requirements of Prism Desk.

Functional requirements describe what the application does. Non-functional requirements describe how reliably, securely, and efficiently it must perform those functions.

## 1.2 Initial Deployment Environment

The initial deployment is designed for:

| Component | Requirement |
|---|---|
| Users | Approximately 30 laboratory users |
| Students | Approximately 20 initially |
| Professors | Multiple professors supported |
| Access | Browser-based |
| Network | Laboratory LAN |
| Backend | Python FastAPI |
| Frontend | React + TypeScript |
| Database | PostgreSQL |
| Database hosting | Local laboratory workstation |
| Operating system | Ubuntu Linux |
| Communication | Discord |
| Architecture | Modular monolith |

The architecture should support future expansion without requiring a complete redesign.

---

# 2. Performance Requirements

## 2.1 General Response Time

The application should provide responsive interaction under normal laboratory network conditions.

| Operation | Target response time |
|---|---:|
| Login | ≤ 2 seconds |
| Dashboard loading | ≤ 3 seconds |
| Project listing | ≤ 2 seconds |
| Project details | ≤ 2 seconds |
| Research library search | ≤ 3 seconds |
| Task listing | ≤ 2 seconds |
| Handbook entry loading | ≤ 2 seconds |
| Save handbook entry | ≤ 2 seconds |
| Task submission | ≤ 3 seconds |
| Conference listing | ≤ 2 seconds |

These are initial engineering targets, not guaranteed performance figures. They should be validated through load testing using realistic data volumes.

## 2.2 Concurrent Users

- The system should initially support at least 30 registered laboratory users.
- It should support at least 20 simultaneous active users as an initial testing target.
- Multiple users should be able to access the application simultaneously.
- Concurrent updates must not silently overwrite each other's data.

The backend and database connection pools must be configured appropriately.

## 2.3 Database Performance

- Frequently queried fields should have suitable indexes.
- Database queries should avoid unnecessary repeated requests.
- Large result sets should use pagination.
- Search operations should use appropriate database indexes.
- Transactions should preserve data consistency.
- Database connections must be managed efficiently.

## 2.4 Frontend Performance

- Application pages should load efficiently.
- Large tables should support pagination.
- Components should avoid unnecessary rendering.
- API responses should be cached where appropriate.
- The interface should not reload the entire application after every operation.

---

# 3. Security Requirements

Security is a critical requirement because Prism Desk contains laboratory research information and private student records.

## 3.1 Authentication

The system must:
- Authenticate users using username or email and password.
- Store passwords using a secure password-hashing algorithm.
- Support password reset.
- Reject unapproved accounts.
- Reject deactivated accounts.
- Provide secure logout.
- Automatically expire inactive sessions.

Passwords must never be stored in plaintext.

## 3.2 Session Security

Use server-managed sessions with secure cookies.

Recommended cookie properties:
- HttpOnly.
- Secure when deployed over HTTPS.
- SameSite configured appropriately.

Additional requirements:
- Session identifiers must be unpredictable.
- Session identifiers must be rotated after authentication.
- Logout must invalidate the server-side session.
- Expired sessions must not remain usable.
- CSRF protection must be implemented where required by the chosen cookie-based authentication design.

Do not store authentication secrets in browser localStorage.

## 3.3 Role-Based Access Control

The system must enforce role-based and resource-level permissions.

Required roles:
- Administrator.
- Professor.
- Student.
- Guest.

Requirements:
- Users may have multiple roles.
- Permissions must be checked on the backend.
- Frontend visibility must not be treated as a security mechanism.
- Project access must be checked for every protected operation.
- Guest permissions must be explicitly assigned.

## 3.4 Data Privacy

The system must protect:
- Personal research notes.
- Private task submissions.
- Student handbook records.
- Account information.
- Discord account mappings.
- Administrative records.

Privacy requirements:
- Professors cannot view personal research notes.
- Administrators cannot view personal research notes by default.
- Students cannot view other students' private submissions.
- Guests must not access unauthorised project information.

## 3.5 API Security

The FastAPI backend must:
- Validate incoming data using Pydantic.
- Authenticate protected requests.
- Enforce resource-level authorisation.
- Apply rate limiting to sensitive endpoints where appropriate.
- Handle invalid input safely.
- Avoid exposing internal stack traces to users.
- Use secure CORS configuration.
- Protect against SQL injection through safe ORM/query practices.
- Protect against cross-site scripting through appropriate input handling and output rendering.
- Protect against CSRF where applicable.

## 3.6 Discord Security

The Discord integration must:
- Use secure account verification.
- Protect OAuth credentials and bot tokens.
- Store secrets outside source code.
- Use minimum required Discord permissions.
- Prevent notification of private information to public channels.
- Validate Discord integration responses.
- Support token revocation and account unlinking.

## 3.7 Audit Security

- Important actions must be recorded.
- Audit records must not be editable by ordinary users.
- Audit access must be restricted by role.
- Passwords and authentication secrets must never be logged.
- Private research notes must not be included in audit records.

---

# 4. Reliability and Availability

## 4.1 Application Reliability

The application should remain operational during normal laboratory working hours.

The initial target is at least **99% availability during scheduled laboratory operating hours**, excluding planned maintenance and external infrastructure failures.

This target must be measured after deployment.

## 4.2 Database Reliability

- PostgreSQL must be the central source of truth.
- Important database operations must use transactions.
- Failed operations must not leave partially updated records.
- Database constraints must protect data integrity.
- Database connection failures must be handled gracefully.

## 4.3 Discord Failure Handling

Discord is an external dependency.

If Discord becomes unavailable:
- Users must still be able to log in.
- Projects must remain accessible.
- Tasks must still be created and updated.
- Research records must still be saved.
- Handbook entries must still be saved.
- Conference deadlines must still be maintained.

Failed Discord notifications must be logged and retried according to a configurable retry policy.

Discord failure must not interrupt core application operations.

## 4.4 Error Handling

The application must provide understandable error messages.

Examples:
- Database temporarily unavailable.
- Session expired.
- Permission denied.
- Invalid input.
- Discord notification failed.
- Requested record not found.

Technical details and stack traces must be recorded in application logs rather than displayed to ordinary users.

---

# 5. Backup and Disaster Recovery

## 5.1 Database Backup

PostgreSQL must be backed up automatically.

Initial backup policy:
- One automated backup per day.
- Backup stored on the laboratory workstation.
- Backup files must be protected from unauthorised access.
- Backup success or failure must be logged.
