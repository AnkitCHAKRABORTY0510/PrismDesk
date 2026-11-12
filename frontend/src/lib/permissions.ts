import type { User } from "../services/authService";

// Capabilities come from the backend (/auth/me) so the frontend never
// duplicates role rules. Hiding UI is a convenience; the API enforces
// every permission.
export function can(user: User | null, capability: string): boolean {
  return Boolean(user?.capabilities?.includes(capability));
}

export interface NavItem {
  label: string;
  to: string;
  capability?: string;
  section: "Workspace" | "Administration" | "Account";
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", section: "Workspace" },
  { label: "Projects", to: "/projects", capability: "projects.view", section: "Workspace" },
  { label: "Research Library", to: "/research", capability: "research.view", section: "Workspace" },
  { label: "Tasks", to: "/tasks", capability: "tasks.view", section: "Workspace" },
  { label: "Handbook", to: "/handbook", capability: "handbook.view", section: "Workspace" },
  { label: "Conferences", to: "/conferences", section: "Workspace" },
  { label: "Journals", to: "/journals", capability: "journals.view", section: "Workspace" },
  { label: "User Management", to: "/admin/users", capability: "users.manage", section: "Administration" },
  { label: "Audit Logs", to: "/admin/audit", capability: "audit.view", section: "Administration" },
  { label: "Announcements", to: "/admin/announcements", capability: "announcements.send", section: "Administration" },
  { label: "System Settings", to: "/admin/settings", capability: "settings.view", section: "Administration" },
  { label: "Notifications", to: "/settings/notifications", capability: "notifications.manage_own", section: "Account" },
];

export function navigationFor(user: User | null): NavItem[] {
  return NAV_ITEMS.filter((item) => !item.capability || can(user, item.capability));
}

export function primaryRole(user: User | null): string {
  if (!user) return "";
  for (const role of ["Administrator", "Professor", "Student", "Guest"]) {
    if (user.roles.includes(role)) return role;
  }
  return user.roles[0] ?? "";
}
