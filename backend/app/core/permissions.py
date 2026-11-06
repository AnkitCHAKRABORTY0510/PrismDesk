"""Central definition of global roles and the capabilities they grant.

Project-level rights are evaluated separately in
``app.services.project_access``. The frontend receives the capability
list from ``/auth/me`` so it never re-implements role logic.
"""

ADMINISTRATOR = "Administrator"
PROFESSOR = "Professor"
STUDENT = "Student"
GUEST = "Guest"

ALL_ROLES = (ADMINISTRATOR, PROFESSOR, STUDENT, GUEST)

# Roles that public registration or approval may grant without an
# explicit administrator role-management action.
APPROVAL_ROLES = (STUDENT, PROFESSOR, GUEST)

ROLE_CAPABILITIES: dict[str, set[str]] = {
    ADMINISTRATOR: {
        "users.manage",
        "audit.view",
        "settings.view",
        "announcements.send",
        "projects.view",
        "projects.create",
        "projects.view_all",
        "research.view",
        "research.create",
        "tasks.view",
        "tasks.create_official",
        "tasks.review",
        "handbook.view",
        "handbook.review",
        "conferences.view",
        "conferences.create",
        "dashboard.admin",
    },
    PROFESSOR: {
        "projects.view",
        "projects.create",
        "research.view",
        "research.create",
        "tasks.view",
        "tasks.create_official",
        "tasks.review",
        "handbook.view",
        "handbook.review",
        "conferences.view",
        "conferences.create",
        "dashboard.professor",
    },
    STUDENT: {
        "projects.view",
        "projects.create",
        "research.view",
        "research.create",
        "research.track_progress",
        "tasks.view",
        "tasks.personal",
        "handbook.view",
        "handbook.write",
        "conferences.view",
        "conferences.create",
        "dashboard.student",
    },
    GUEST: {
        "projects.view",
        "dashboard.guest",
    },
}

# Every approved user can manage their own notification settings.
COMMON_CAPABILITIES = {"notifications.manage_own"}


def capabilities_for(role_names: set[str] | list[str]) -> set[str]:
    capabilities = set(COMMON_CAPABILITIES)

    for role_name in role_names:
        capabilities |= ROLE_CAPABILITIES.get(role_name, set())

    return capabilities


def has_capability(role_names: set[str], capability: str) -> bool:
    return capability in capabilities_for(role_names)
