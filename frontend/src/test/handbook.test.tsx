import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authService from "../services/authService";
import * as handbookService from "../services/handbookService";
import * as plannerService from "../services/handbookPlannerService";
import * as projectService from "../services/projectService";
import { activityLevel, addDays, addMonths, longDayLabel, monthWeeks, today, writingStreak } from "../lib/calendar";
import { CalendarView, type CalendarMode } from "../pages/handbook/CalendarView";
import { DayPage } from "../pages/handbook/DayPage";
import Handbook from "../pages/handbook/Handbook";
import { EMPTY_DAY, parseReferences, type DayInfo } from "../pages/handbook/plannerMeta";
import { ADMIN_CAPS, STUDENT_CAPS, makeUser, renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  registerUser: vi.fn(),
}));
vi.mock("../services/projectService", () => ({ listProjects: vi.fn(), listMembers: vi.fn() }));
vi.mock("../services/handbookService", () => ({
  listEntries: vi.fn(),
  listSummaries: vi.fn(),
  progress: vi.fn(),
  createSummary: vi.fn(),
  updateSummary: vi.fn(),
  summaryVersions: vi.fn(),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  listSharedNotes: vi.fn(),
  createSharedNote: vi.fn(),
  updateSharedNote: vi.fn(),
  sharedNoteVersions: vi.fn(),
  addSharedComment: vi.fn(),
}));
vi.mock("../services/handbookPlannerService", () => ({
  PLANNER_CHANGED: "handbook:planner-changed",
  getPlanner: vi.fn(),
  createTodo: vi.fn(),
  updateTodo: vi.fn(),
  deleteTodo: vi.fn(),
  reorderTodos: vi.fn(),
  carryForward: vi.fn(),
  createPin: vi.fn(),
  deletePin: vi.fn(),
  createReminder: vi.fn(),
  updateReminder: vi.fn(),
  deleteReminder: vi.fn(),
  upcomingReminders: vi.fn(),
  openTodos: vi.fn(),
}));

// Node's own experimental localStorage can shadow jsdom's; use a plain
// in-memory Storage so draft/autosave behaviour is testable.
const memory = new Map<string, string>();
Object.defineProperty(window, "localStorage", {
  configurable: true,
  value: {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => void memory.set(key, String(value)),
    removeItem: (key: string) => void memory.delete(key),
    clear: () => memory.clear(),
    key: (index: number) => [...memory.keys()][index] ?? null,
    get length() {
      return memory.size;
    },
  },
});

const auth = vi.mocked(authService);
const handbook = vi.mocked(handbookService);
const planner = vi.mocked(plannerService);
const projects = vi.mocked(projectService);
const empty = { items: [], total: 0, page: 1, page_size: 20 };
const TODAY = today();
const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// Day buttons are named with the viewer's locale date, then details.
const dayButton = (iso: string, details = "") => new RegExp(`^${escape(longDayLabel(iso))}${details}`);

function pin(id: string, day: string, label: string) {
  return { id, pin_date: day, label, category: "deadline" as const, note: "", created_at: "", updated_at: "" };
}

function todo(id: string, day: string, text: string, position = 0) {
  return { id, todo_date: day, text, done: false, position, done_at: null, created_at: "", updated_at: "" };
}

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  auth.getCurrentUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS));
  handbook.listEntries.mockResolvedValue(empty);
  handbook.listSummaries.mockResolvedValue(empty);
  handbook.progress.mockResolvedValue([]);
  handbook.listSharedNotes.mockResolvedValue(empty);
  planner.getPlanner.mockResolvedValue({ pins: [], todos: [], reminders: [] });
  planner.upcomingReminders.mockResolvedValue([]);
  planner.openTodos.mockResolvedValue([]);
  projects.listProjects.mockResolvedValue(empty);
});

describe("calendar helpers", () => {
  it("builds Monday-first month grids and clamps month arithmetic", () => {
    const weeks = monthWeeks("2026-11-11");
    expect(weeks[0][0]).toBe("2026-10-26");
    expect(weeks.at(-1)?.[6]).toBe("2026-12-06");
    expect(addMonths("2027-01-31", 1)).toBe("2027-02-28");
    expect(addDays("2026-03-29", 1)).toBe("2026-03-30");
  });

  it("counts a writing streak that is not broken before today is written", () => {
    const days = new Set(["2026-11-08", "2026-11-09", "2026-11-10"]);
    expect(writingStreak(days, "2026-11-11")).toBe(3);
    expect(writingStreak(days, "2026-11-12")).toBe(0);
    expect(activityLevel(0, 0)).toBe(0);
    expect(activityLevel(2, 300)).toBe(4);
  });

  it("validates references line by line", () => {
    expect(parseReferences("https://a.org\n\nftp://x\nnot a url").error).toBe("Lines 3, 4 are not valid links (start with https://).");
    expect(parseReferences(" https://arxiv.org/abs/1 \n").urls).toEqual(["https://arxiv.org/abs/1"]);
  });
});

function CalendarHarness({ days = new Map<string, DayInfo>(), onOpen = vi.fn() }: { days?: Map<string, DayInfo>; onOpen?: (day: string) => void }) {
  const [focused, setFocused] = useState("2026-11-11");
  const [mode, setMode] = useState<CalendarMode>("month");
  return <CalendarView focused={focused} onFocus={setFocused} onOpen={onOpen} mode={mode} onModeChange={setMode} days={days} />;
}

describe("Calendar view", () => {
  it("shows pins, reminders and to-dos in day cells", () => {
    const days = new Map<string, DayInfo>([
      ["2026-11-20", { ...EMPTY_DAY, journalWords: 40, entries: 1, pins: [pin("p1", "2026-11-20", "Camera-ready")], todos: [todo("t1", "2026-11-20", "Plot"), todo("t2", "2026-11-20", "Write")] }],
    ]);
    renderWithProviders(<CalendarHarness days={days} />);
    const cell = screen.getByRole("button", { name: dayButton("2026-11-20", ", journal written, 1 project entry, pins: Camera-ready, 2 open to-dos") });
    expect(cell).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "November 2026" })).toBeInTheDocument();
  });

  it("moves focus with arrow keys, pages months, and opens a day with Enter", async () => {
    const onOpen = vi.fn();
    renderWithProviders(<CalendarHarness onOpen={onOpen} />);
    const start = screen.getByRole("button", { name: dayButton("2026-11-11") });
    expect(start).toHaveAttribute("tabindex", "0");
    start.focus();

    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: dayButton("2026-11-12") })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: dayButton("2026-11-19") })).toHaveFocus();
    await userEvent.keyboard("{PageDown}");
    expect(screen.getByRole("heading", { name: "December 2026" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: dayButton("2026-12-19") })).toHaveFocus();

    await userEvent.keyboard("{Enter}");
    expect(onOpen).toHaveBeenCalledWith("2026-12-19");
  });

  it("switches to the week view and jumps by month and year", async () => {
    renderWithProviders(<CalendarHarness />);
    await userEvent.selectOptions(screen.getByLabelText("Jump to year"), "2027");
    expect(screen.getByRole("heading", { name: "November 2027" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Week" }));
    expect(screen.getByRole("heading", { name: /Week of/ })).toBeInTheDocument();
    expect(within(screen.getByRole("grid")).getAllByRole("gridcell")).toHaveLength(7);
  });
});

describe("Day page", () => {
  const summary = {
    id: "s1",
    entry_date: TODAY,
    summary: "Ran the ablation study.",
    challenges: "",
    plan_next: "Write results",
    version: 2,
    created_at: "2026-11-11T08:00:00Z",
    updated_at: "2026-11-11T09:00:00Z",
  };

  function renderDay(day = TODAY, props: Partial<Parameters<typeof DayPage>[0]> = {}) {
    const handlers = { onNavigate: vi.fn(), onClose: vi.fn(), onChanged: vi.fn() };
    renderWithProviders(<DayPage day={day} userId="u1" canWrite {...handlers} {...props} />);
    return handlers;
  }

  it("opens an existing journal in read mode and saves an edit as a new version", async () => {
    handbook.listSummaries.mockResolvedValue({ ...empty, items: [summary], total: 1 });
    handbook.updateSummary.mockResolvedValue({ ...summary, summary: "Ran the ablation study twice.", version: 3 });
    const { onChanged } = renderDay();

    expect(await screen.findByText("Ran the ablation study.")).toBeInTheDocument();
    expect(screen.getByText(/version 2/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    const box = screen.getByLabelText("What I did today");
    await userEvent.type(box, " twice");
    expect(screen.getByText(/Unsaved changes/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save journal" }));

    await waitFor(() =>
      expect(handbook.updateSummary).toHaveBeenCalledWith("s1", { summary: "Ran the ablation study. twice", challenges: "", plan_next: "Write results" })
    );
    expect(await screen.findByText("Ran the ablation study twice.")).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
  });

  it("keeps a local draft and warns before closing with unsaved text", async () => {
    const { onClose } = renderDay();
    const box = await screen.findByLabelText("What I did today");
    await userEvent.type(box, "Draft words");
    await waitFor(() => expect(window.localStorage.getItem(`prismdesk.handbook.draft.u1.${TODAY}`)).toContain("Draft words"), { timeout: 2000 });

    await userEvent.click(screen.getByRole("button", { name: "Close day page" }));
    expect(screen.getByRole("alertdialog", { name: "Unsaved changes" })).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Close anyway" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("blocks writing on future days but lets the user plan to-dos", async () => {
    const future = addDays(TODAY, 3);
    planner.createTodo.mockResolvedValue(todo("t1", future, "Book the GPU"));
    renderDay(future);

    expect(await screen.findByText("This page is still blank.")).toBeInTheDocument();
    expect(screen.queryByLabelText("What I did today")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add project entry" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Add to-dos" }));
    await userEvent.type(await screen.findByLabelText("New to-do"), "Book the GPU");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(planner.createTodo).toHaveBeenCalledWith(future, "Book the GPU"));
  });

  it("pages to the next day with the arrow button and keyboard", async () => {
    const { onNavigate } = renderDay();
    await screen.findByLabelText("What I did today");
    await userEvent.click(screen.getByRole("button", { name: "Next day" }));
    expect(onNavigate).toHaveBeenCalledWith(addDays(TODAY, 1));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "ArrowLeft" });
    expect(onNavigate).toHaveBeenLastCalledWith(addDays(TODAY, -1));
  });

  it("reorders and carries forward to-dos", async () => {
    planner.getPlanner.mockResolvedValue({ pins: [], reminders: [], todos: [todo("a", TODAY, "First", 0), todo("b", TODAY, "Second", 1)] });
    planner.reorderTodos.mockResolvedValue([]);
    planner.carryForward.mockResolvedValue([]);
    renderDay(TODAY, { initialSection: "todos" });

    await userEvent.click(await screen.findByRole("button", { name: 'Move "Second" up' }));
    await waitFor(() => expect(planner.reorderTodos).toHaveBeenCalledWith(TODAY, ["b", "a"]));
    await userEvent.click(screen.getByRole("button", { name: "Carry 2 unfinished to tomorrow" }));
    await waitFor(() => expect(planner.carryForward).toHaveBeenCalledWith(TODAY, addDays(TODAY, 1)));
  });
});

describe("Handbook page", () => {
  it("opens the day page from the calendar and keeps the list view reachable", async () => {
    planner.getPlanner.mockResolvedValue({ pins: [pin("p1", TODAY, "Lab meeting")], todos: [], reminders: [] });
    renderWithProviders(<Handbook />, "/handbook");

    const todayCell = await screen.findByRole("button", { name: /today.*pins: Lab meeting/ });
    await userEvent.click(todayCell);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(await screen.findByLabelText("What I did today")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close day page" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "List" }));
    expect(await screen.findByText("No handbook entries yet")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "My journal (private)" })).toBeInTheDocument();
  });

  it("still shows the journal calendar when the planner is unavailable", async () => {
    planner.getPlanner.mockRejectedValue(new Error("Network Error"));
    handbook.progress.mockResolvedValue([{ entry_date: TODAY, entry_count: 1, student_count: 1 }]);
    renderWithProviders(<Handbook />, "/handbook");

    expect(await screen.findByText(/Pins, to-dos and reminders are unavailable right now/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: dayButton(TODAY, ", today, 1 project entry") })).toBeInTheDocument();
  });
});

describe("Shared with supervisor", () => {
  const student = { id: "u1", username: "s", full_name: "Sam Student", roles: ["Student"] };
  const note = {
    id: "n1",
    student,
    entry_date: TODAY,
    body: "Blocked on the GPU queue.",
    version: 1,
    created_at: "2026-11-11T08:00:00Z",
    updated_at: "2026-11-11T08:00:00Z",
    comment_count: 0,
    comments: [],
    can_edit: true,
    can_comment: false,
  };

  it("keeps private notes and the shared note in separate, labelled sections", async () => {
    handbook.createSharedNote.mockResolvedValue({ ...note, body: "Need help with the loader" });
    renderWithProviders(<DayPage day={TODAY} userId="u1" canWrite onNavigate={vi.fn()} onClose={vi.fn()} onChanged={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Private notes" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Shared with supervisor" })).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: /Write a note for your supervisor/ }));
    await userEvent.type(screen.getByLabelText("Note shared with your supervisors"), "Need help with the loader");
    await userEvent.click(screen.getByRole("button", { name: "Share with supervisor" }));

    await waitFor(() => expect(handbook.createSharedNote).toHaveBeenCalledWith(TODAY, "Need help with the loader"));
    expect(handbook.createSummary).not.toHaveBeenCalled();
    expect(await screen.findByText("Need help with the loader")).toBeInTheDocument();
  });

  it("shows supervisors their students' shared notes, lets them comment, and never loads private notes", async () => {
    auth.getCurrentUser.mockResolvedValue(makeUser(["Administrator"], ADMIN_CAPS));
    handbook.listSharedNotes.mockResolvedValue({ ...empty, items: [{ ...note, can_edit: false, can_comment: true }], total: 1 });
    handbook.addSharedComment.mockResolvedValue({
      ...note,
      can_edit: false,
      can_comment: true,
      comment_count: 1,
      comments: [{ id: "c1", note_id: "n1", parent_id: null, author: null, body: "Use the night queue", created_at: "2026-11-11T09:00:00Z", replies: [] }],
    });
    renderWithProviders(<DayPage day={TODAY} userId="admin" canWrite={false} onNavigate={vi.fn()} onClose={vi.fn()} onChanged={vi.fn()} />);

    expect(await screen.findByText("Blocked on the GPU queue.")).toBeInTheDocument();
    expect(screen.getByText("Sam Student")).toBeInTheDocument();
    expect(handbook.listSummaries).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "Private notes" })).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Comment on Sam Student's note"), "Use the night queue");
    await userEvent.click(screen.getByRole("button", { name: "Comment" }));
    await waitFor(() => expect(handbook.addSharedComment).toHaveBeenCalledWith("n1", "Use the night queue", undefined));
    expect(await screen.findByText("Use the night queue")).toBeInTheDocument();
  });

  it("marks days with a shared note on the calendar", async () => {
    handbook.listSharedNotes.mockResolvedValue({ ...empty, items: [note], total: 1 });
    renderWithProviders(<Handbook />, "/handbook");
    expect(await screen.findByRole("button", { name: dayButton(TODAY, ", today, shared note") })).toBeInTheDocument();
  });
});
