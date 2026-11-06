import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AppLayout from "../components/layout/AppLayout";
import EntryFormModal from "../pages/handbook/EntryFormModal";
import ProjectList from "../pages/projects/ProjectList";
import NotificationSettings from "../pages/settings/NotificationSettings";
import TaskDetail from "../pages/tasks/TaskDetail";
import * as authService from "../services/authService";
import * as handbookService from "../services/handbookService";
import * as notificationService from "../services/notificationService";
import * as projectService from "../services/projectService";
import * as taskService from "../services/taskService";
import { ADMIN_CAPS, GUEST_CAPS, STUDENT_CAPS, makeUser, renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  registerUser: vi.fn(),
}));
vi.mock("../services/projectService", () => ({ listProjects: vi.fn(), listMembers: vi.fn() }));
vi.mock("../services/taskService", () => ({
  getTask: vi.fn(),
  listSubmissions: vi.fn(),
  submitWork: vi.fn(),
  changeStatus: vi.fn(),
}));
vi.mock("../services/handbookService", () => ({ createEntry: vi.fn(), updateEntry: vi.fn() }));
vi.mock("../services/notificationService", () => ({
  discordStatus: vi.fn(),
  getPreferences: vi.fn(),
  savePreferences: vi.fn(),
  myNotifications: vi.fn(),
  startDiscordLink: vi.fn(),
  unlinkDiscord: vi.fn(),
}));

const auth = vi.mocked(authService);
const projects = vi.mocked(projectService);
const tasks = vi.mocked(taskService);
const handbook = vi.mocked(handbookService);
const notifications = vi.mocked(notificationService);

const owner = { id: "u1", username: "owner", full_name: "Owner One", roles: ["Student"] };

function project(id: string, title: string) {
  return {
    id,
    title,
    description: "",
    objectives: "",
    status: "active" as const,
    owner,
    created_by: "u1",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-02T00:00:00Z",
    archive_requested_at: null,
    archive_request_reason: null,
    archived_at: null,
    deleted_at: null,
    purge_eligible_at: null,
    member_count: 2,
    supervisors: [],
    my_role: "owner" as const,
    permissions: {
      can_edit: true, can_contribute: true, can_manage_members: false, can_archive: false, can_unarchive: false,
      can_request_archive: true, can_delete: false, can_restore: false, can_review: false,
    },
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  auth.getCurrentUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS));
});

describe("Role-based app shell", () => {
  const shell = (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<p>content</p>} />
      </Route>
    </Routes>
  );

  it("hides administration links from students", async () => {
    renderWithProviders(shell, "/dashboard");
    const nav = await screen.findByRole("complementary", { name: "Main navigation" });
    await waitFor(() => expect(within(nav).getByText("Handbook")).toBeInTheDocument());
    expect(within(nav).queryByText("User Management")).not.toBeInTheDocument();
  });

  it("shows administration links to administrators", async () => {
    auth.getCurrentUser.mockResolvedValue(makeUser(["Administrator"], ADMIN_CAPS));
    renderWithProviders(shell, "/dashboard");
    expect(await screen.findByText("User Management")).toBeInTheDocument();
    expect(screen.getByText("Audit Logs")).toBeInTheDocument();
  });

  it("gives guests no task or handbook links", async () => {
    auth.getCurrentUser.mockResolvedValue(makeUser(["Guest"], GUEST_CAPS));
    renderWithProviders(shell, "/dashboard");
    expect(await screen.findByText("Conferences")).toBeInTheDocument();
    expect(screen.queryByText("Tasks")).not.toBeInTheDocument();
    expect(screen.queryByText("Handbook")).not.toBeInTheDocument();
  });
});

describe("Project list", () => {
  it("renders rows and sends search and filter parameters", async () => {
    projects.listProjects.mockResolvedValue({ items: [project("p1", "Spectral imaging")], total: 1, page: 1, page_size: 20 });
    renderWithProviders(<ProjectList />, "/projects");

    expect(await screen.findByText("Spectral imaging")).toBeInTheDocument();
    expect(screen.getByText("1 result · page 1 of 1")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Search"), "spec");
    await userEvent.selectOptions(screen.getByLabelText("Project status"), "archived");

    await waitFor(() =>
      expect(projects.listProjects).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "spec", status: "archived", page: 1 })
      )
    );
    // Students cannot browse deleted projects.
    expect(screen.queryByRole("option", { name: "Deleted (recoverable)" })).not.toBeInTheDocument();
  });
});

describe("Task workflow", () => {
  const assignment = {
    id: "a1",
    task_id: "t1",
    assignee: owner,
    status: "in_progress" as const,
    assigned_at: "2026-11-01T00:00:00Z",
    submitted_at: null,
    completed_at: null,
    updated_at: "2026-11-01T00:00:00Z",
    submission_count: 0,
  };
  const task = {
    id: "t1",
    task_type: "official" as const,
    title: "Literature survey",
    description: "Survey ten papers",
    project_id: "p1",
    project_title: "Spectral imaging",
    created_by: "prof",
    priority: "high" as const,
    due_at: null,
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
    is_overdue: false,
    my_assignment: assignment,
    assignments: [assignment],
    can_manage: false,
  };

  it("lets an assignee submit text and external links", async () => {
    tasks.getTask.mockResolvedValue(task);
    tasks.listSubmissions.mockResolvedValue([]);
    tasks.submitWork.mockResolvedValue({ id: "s1", assignment_id: "a1", version: 1, response_text: "Done", links: [], submitted_at: "", reviews: [] });

    renderWithProviders(
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetail />} />
      </Routes>,
      "/tasks/t1"
    );

    await userEvent.type(await screen.findByLabelText("Response"), "Done");
    await userEvent.type(screen.getByLabelText("External links"), "https://github.com/lab/a, https://overleaf.com/b");
    await userEvent.click(screen.getByRole("button", { name: "Submit for review" }));

    await waitFor(() =>
      expect(tasks.submitWork).toHaveBeenCalledWith("a1", "Done", ["https://github.com/lab/a", "https://overleaf.com/b"])
    );
    // Students never see review controls on their own work.
    expect(screen.queryByRole("button", { name: "Approve & complete" })).not.toBeInTheDocument();
  });

  it("offers only the allowed status moves", async () => {
    tasks.getTask.mockResolvedValue({ ...task, my_assignment: { ...assignment, status: "todo" }, assignments: [{ ...assignment, status: "todo" }] });
    tasks.listSubmissions.mockResolvedValue([]);
    renderWithProviders(
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetail />} />
      </Routes>,
      "/tasks/t1"
    );
    expect(await screen.findByRole("button", { name: "Move to In progress" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Move to Completed" })).not.toBeInTheDocument();
  });
});

describe("Handbook entry form", () => {
  it("requires some content before saving", async () => {
    projects.listProjects.mockResolvedValue({ items: [project("p1", "Spectral imaging")], total: 1, page: 1, page_size: 100 });
    renderWithProviders(<EntryFormModal open onClose={() => undefined} onSaved={() => undefined} />);

    await userEvent.selectOptions(await screen.findByLabelText("Project"), "p1");
    await userEvent.click(screen.getByRole("button", { name: "Save entry" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Describe at least one part");
    expect(handbook.createEntry).not.toHaveBeenCalled();
  });
});

describe("Notification settings", () => {
  it("saves toggled categories and explains missing Discord configuration", async () => {
    notifications.discordStatus.mockResolvedValue({ linked: false, discord_username: null, linked_at: null, oauth_configured: false, bot_configured: false });
    notifications.getPreferences.mockResolvedValue([
      { category: "tasks", enabled: true },
      { category: "handbook", enabled: true },
    ]);
    notifications.myNotifications.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 });
    notifications.savePreferences.mockImplementation(async (prefs) => prefs);

    renderWithProviders(<NotificationSettings />, "/settings/notifications");

    expect(await screen.findByText(/has not been configured on this server/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Link with Discord" })).not.toBeInTheDocument();

    await userEvent.click(await screen.findByLabelText("Handbook notifications"));
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    await waitFor(() =>
      expect(notifications.savePreferences).toHaveBeenCalledWith([
        { category: "tasks", enabled: true },
        { category: "handbook", enabled: false },
      ])
    );
  });
});
