import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingStatusToggle } from "../components/research/ReadingStatusToggle";
import Dashboard from "../pages/dashboard/Dashboard";
import RepoLinksCard from "../pages/projects/RepoLinksCard";
import * as authService from "../services/authService";
import * as dashboardService from "../services/dashboardService";
import type { StudentDashboardData } from "../services/dashboardService";
import * as projectService from "../services/projectService";
import type { Project } from "../services/projectService";
import * as researchService from "../services/researchService";
import { STUDENT_CAPS, makeUser, renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({ getCurrentUser: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn() }));
vi.mock("../services/dashboardService", () => ({
  adminDashboard: vi.fn(),
  professorDashboard: vi.fn(),
  studentDashboard: vi.fn(),
  guestDashboard: vi.fn(),
}));
vi.mock("../services/researchService", () => ({ setReadingStatus: vi.fn() }));
vi.mock("../services/projectService", () => ({ listRepoLinks: vi.fn(), addRepoLink: vi.fn(), removeRepoLink: vi.fn() }));

const auth = vi.mocked(authService);
const dashboard = vi.mocked(dashboardService);
const research = vi.mocked(researchService);
const projects = vi.mocked(projectService);

const inDays = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString();

function studentData(): StudentDashboardData {
  const counts = (c: Record<string, number>) => ({ counts: c, total: Object.values(c).reduce((a, b) => a + b, 0) });
  return {
    joined_projects: [
      {
        id: "p1",
        title: "Spectral Imaging Pipeline",
        status: "active",
        my_role: "member",
        member_count: 4,
        assignments_total: 4,
        assignments_completed: 1,
        pending_reviews: 0,
        overdue: 0,
        assignment_counts: { todo: 1, in_progress: 1, under_review: 1, revision_required: 0, completed: 1 },
        members: [{ user_id: "u1", username: "maya", full_name: "Maya Chen", membership_role: "member" }],
        repo_links: [{ url: "https://github.com/prism-lab/spectral-pipeline", label: null }],
      },
    ],
    owned_project_count: 0,
    assigned_tasks: counts({ todo: 1, in_progress: 1, under_review: 1, revision_required: 0, completed: 1 }),
    personal_tasks: counts({ todo: 2, in_progress: 0, completed: 1 }),
    pending_submissions: 2,
    task_completion_rate: 0.25,
    reading_progress: counts({ not_started: 1, reading: 1, completed: 0 }),
    handbook_entries_last_7_days: 3,
    handbook_entries_last_30_days: 9,
    recent_handbook_entries: [],
    upcoming_deadlines: [
      { id: "t1", title: "Calibrate sensor", due_at: inDays(2), kind: "task", project_id: "p1", project_title: "Spectral Imaging Pipeline", status: null },
    ],
    reading_list: [
      { paper_id: "r1", title: "Deep spectral unmixing", venue: "CVPR", publication_year: 2023, status: "reading" },
      { paper_id: "r2", title: "Tiny ML on MCUs", venue: null, publication_year: null, status: "not_started" },
    ],
    handbook_days: [],
    handbook_streak: 3,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  auth.getCurrentUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS, { full_name: "Maya Chen" }));
  dashboard.studentDashboard.mockResolvedValue(studentData());
});

describe("Spectrum dashboard", () => {
  it("renders the banner, pipeline links, project tile repo link and reading counts", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>,
      "/dashboard"
    );

    expect(await screen.findByRole("heading", { level: 1, name: /Maya/ })).toBeInTheDocument();
    const status = screen.getByRole("list", { name: "Status" });
    expect(within(status).getByRole("link", { name: /Calibrate sensor in 2 days/ })).toHaveAttribute("href", "/tasks/t1");

    const pipeline = screen.getByRole("region", { name: "Tasks" });
    expect(within(pipeline).getByRole("link", { name: /Submitted/ })).toHaveAttribute("href", "/tasks?view=mine&status=under_review");

    expect(screen.getByRole("link", { name: /prism-lab\/spectral-pipeline/ })).toHaveAttribute(
      "href",
      "https://github.com/prism-lab/spectral-pipeline"
    );

    const reading = screen.getByRole("region", { name: "Reading list" });
    expect(within(reading).getByRole("group", { name: /Deep spectral unmixing/ })).toBeInTheDocument();
  });

  it("updates reading counts optimistically when a status is toggled", async () => {
    research.setReadingStatus.mockResolvedValue({} as never);
    renderWithProviders(
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>,
      "/dashboard"
    );
    const reading = await screen.findByRole("region", { name: "Reading list" });
    const group = within(reading).getByRole("group", { name: /Deep spectral unmixing/ });
    await userEvent.click(within(group).getByRole("button", { name: /Completed/ }));

    expect(within(group).getByRole("button", { name: /Completed/ })).toHaveAttribute("aria-pressed", "true");
    expect(research.setReadingStatus).toHaveBeenCalledWith("r1", "completed");
    // Counts follow optimistically: completed 0 → 1, reading 1 → 0.
    expect(within(reading).getByTestId("reading-count-completed")).toHaveTextContent("Completed1");
    expect(within(reading).getByTestId("reading-count-reading")).toHaveTextContent("Reading0");
  });
});

describe("Reading status toggle", () => {
  it("reverts when saving fails", async () => {
    research.setReadingStatus.mockRejectedValue(new Error("offline"));
    const onChange = vi.fn();
    renderWithProviders(<ReadingStatusToggle paperId="x" paperTitle="Paper X" status="reading" onChange={onChange} />);
    const done = await screen.findByRole("button", { name: /Completed/ });
    await userEvent.click(done);
    await waitFor(() => expect(onChange).toHaveBeenLastCalledWith("reading"));
    expect(screen.getByRole("button", { name: /Reading/ })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("Project Code card", () => {
  const project = { id: "p1", permissions: { can_contribute: true } } as unknown as Project;

  it("validates GitHub links and adds one", async () => {
    projects.listRepoLinks.mockResolvedValue([]);
    projects.addRepoLink.mockResolvedValue({
      id: "l1",
      project_id: "p1",
      url: "https://github.com/prism-lab/mesh-sim",
      label: null,
      added_by: "u1",
      added_by_username: "maya",
      created_at: "2026-11-11T00:00:00Z",
      can_remove: true,
    });
    renderWithProviders(<RepoLinksCard project={project} />);
    await userEvent.click(await screen.findByRole("button", { name: /Add repository/ }));
    const input = screen.getByLabelText("GitHub repository URL");
    await userEvent.type(input, "https://gitlab.com/a/b");
    expect(screen.getByText(/Use a link like/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Link repository" })).toBeDisabled();

    await userEvent.clear(input);
    await userEvent.type(input, "https://github.com/prism-lab/mesh-sim");
    await userEvent.click(screen.getByRole("button", { name: "Link repository" }));
    expect(projects.addRepoLink).toHaveBeenCalledWith("p1", "https://github.com/prism-lab/mesh-sim", "");
    expect(await screen.findByRole("link", { name: /prism-lab\/mesh-sim/ })).toHaveAttribute("href", "https://github.com/prism-lab/mesh-sim");
  });

  it("hides adding for guests", async () => {
    projects.listRepoLinks.mockResolvedValue([]);
    renderWithProviders(<RepoLinksCard project={{ ...project, permissions: { can_contribute: false } } as unknown as Project} />);
    expect(await screen.findByText(/No repositories linked yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add repository/ })).not.toBeInTheDocument();
  });
});
