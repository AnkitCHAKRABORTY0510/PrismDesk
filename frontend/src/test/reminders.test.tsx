import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReminderFormModal from "../pages/tasks/ReminderFormModal";
import * as authService from "../services/authService";
import * as taskService from "../services/taskService";
import type { Task } from "../services/taskService";
import { ADMIN_CAPS, STUDENT_CAPS, makeUser, renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({ getCurrentUser: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn() }));
vi.mock("../services/taskService", () => ({ createTask: vi.fn(), listTasks: vi.fn(), reminderRecipients: vi.fn() }));
vi.mock("../services/projectService", () => ({ listProjects: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 }) }));

const auth = vi.mocked(authService);
const tasks = vi.mocked(taskService);

const prof = { id: "prof-1", username: "rortiz", full_name: "Rafael Ortiz", roles: ["Professor"] };
const survey = {
  id: "task-1",
  task_type: "official",
  title: "Literature survey",
  description: "",
  project_id: "proj-1",
  project_title: "Spectral Imaging",
  created_by: "prof-1",
  priority: "medium",
  due_at: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
  is_overdue: false,
  my_assignment: null,
  assignments: [],
  can_manage: false,
} as Task;

beforeEach(() => {
  vi.clearAllMocks();
  tasks.reminderRecipients.mockResolvedValue([{ user: prof, membership_role: "supervisor" }]);
  tasks.createTask.mockResolvedValue({ ...survey, id: "rem-1", task_type: "reminder" });
});

describe("Reminder form", () => {
  it("lets a student remind the professor about their task", async () => {
    auth.getCurrentUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS));
    const onSent = vi.fn();
    renderWithProviders(<ReminderFormModal open relatedTask={survey} onClose={() => undefined} onSent={onSent} />);

    expect(await screen.findByRole("dialog", { name: "Remind your professor" })).toBeInTheDocument();
    expect(tasks.reminderRecipients).toHaveBeenCalledWith({ related_task_id: "task-1", project_id: null });
    const send = screen.getByRole("button", { name: /Send reminder/ });
    expect(send).toBeDisabled(); // no recipient yet

    await userEvent.click(await screen.findByRole("checkbox", { name: /Rafael Ortiz/ }));
    await userEvent.type(screen.getByLabelText("Message (optional)"), "Submitted on Monday.");
    await userEvent.click(send);

    expect(tasks.createTask).toHaveBeenCalledWith(
      expect.objectContaining({
        task_type: "reminder",
        title: "Please check: Literature survey",
        description: "Submitted on Monday.",
        related_task_id: "task-1",
        assignee_ids: ["prof-1"],
      })
    );
    expect(onSent).toHaveBeenCalled();
  });

  it("pre-selects the task's assignees for a professor", async () => {
    auth.getCurrentUser.mockResolvedValue(makeUser(["Administrator"], ADMIN_CAPS));
    tasks.reminderRecipients.mockResolvedValue([
      { user: { id: "stu-1", username: "maya", full_name: "Maya Chen", roles: ["Student"] }, membership_role: "member" },
    ]);
    renderWithProviders(
      <ReminderFormModal open relatedTask={{ ...survey, can_manage: true }} defaultRecipientIds={["stu-1"]} onClose={() => undefined} onSent={() => undefined} />
    );
    expect(await screen.findByRole("dialog", { name: "Send a reminder" })).toBeInTheDocument();
    expect(await screen.findByRole("checkbox", { name: /Maya Chen/ })).toBeChecked();
    expect(screen.getByRole("button", { name: /Send reminder/ })).toBeEnabled();
  });
});
