import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

import { ToastProvider } from "../components/ui";
import { AuthProvider } from "../context/AuthContext";
import type { User } from "../services/authService";

export function makeUser(roles: string[], capabilities: string[], overrides: Partial<User> = {}): User {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    username: "tester",
    email: "tester@prismlab.org",
    full_name: "Test User",
    roles,
    capabilities,
    csrf_token: "csrf-token",
    message: "Authenticated user.",
    ...overrides,
  };
}

export const STUDENT_CAPS = [
  "projects.view", "projects.create", "research.view", "research.create", "research.track_progress",
  "tasks.view", "tasks.personal", "handbook.view", "handbook.write", "conferences.view",
  "conferences.create", "dashboard.student", "notifications.manage_own",
];

export const ADMIN_CAPS = [
  "users.manage", "audit.view", "settings.view", "announcements.send", "projects.view", "projects.create",
  "projects.view_all", "research.view", "research.create", "tasks.view", "tasks.create_official",
  "tasks.review", "handbook.view", "handbook.review", "conferences.view", "conferences.create",
  "dashboard.admin", "notifications.manage_own",
];

export const GUEST_CAPS = ["projects.view", "dashboard.guest", "notifications.manage_own"];

export function renderWithProviders(ui: ReactElement, route = "/") {
  return render(
    <AuthProvider>
      <ToastProvider>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

export { vi };
