import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PaperDetail from "../pages/research/PaperDetail";
import ResearchLibrary from "../pages/research/ResearchLibrary";
import * as authService from "../services/authService";
import * as researchService from "../services/researchService";
import type { Paper } from "../services/researchService";
import { GUEST_CAPS, STUDENT_CAPS, makeUser, renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({ getCurrentUser: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn() }));
vi.mock("../services/researchService", () => ({
  listPapers: vi.fn(),
  getPaper: vi.fn(),
  listNotes: vi.fn(),
  deletePaper: vi.fn(),
  createNote: vi.fn(),
  deleteNote: vi.fn(),
  updateNote: vi.fn(),
  setReadingStatus: vi.fn(),
  lookupPaper: vi.fn(),
  createPaper: vi.fn(),
  updatePaper: vi.fn(),
}));

const auth = vi.mocked(authService);
const research = vi.mocked(researchService);

const PAPER_ID = "11111111-1111-1111-1111-111111111111";

function paper(overrides: Partial<Paper> = {}): Paper {
  return {
    id: PAPER_ID,
    title: "Deep spectral unmixing",
    authors: ["A. Rao"],
    abstract: "",
    publication_year: 2023,
    venue: "CVPR",
    doi: null,
    url: null,
    keywords: [],
    added_by: "00000000-0000-0000-0000-000000000001",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
    projects: [],
    my_status: null,
    can_edit: true,
    linked_existing: false,
    discord_thread_url: null,
    ...overrides,
  };
}

function CurrentUrl() {
  const location = useLocation();
  return <div data-testid="url">{`${location.pathname}${location.search}`}</div>;
}

function renderApp(route: string) {
  return renderWithProviders(
    <>
      <Routes>
        <Route path="/research" element={<ResearchLibrary />} />
        <Route path="/research/papers/:paperId" element={<PaperDetail />} />
        <Route path="/dashboard" element={<p>Dashboard</p>} />
      </Routes>
      <CurrentUrl />
    </>,
    route
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  auth.getCurrentUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS));
  research.getPaper.mockResolvedValue(paper());
  research.listNotes.mockResolvedValue([]);
  research.listPapers.mockResolvedValue({ items: [paper()], total: 1, page: 1, page_size: 20 });
  research.deletePaper.mockResolvedValue({ message: "Paper deleted." });
});

describe("Paper detail", () => {
  it("goes back to the library keeping the list's search", async () => {
    renderApp("/research?search=spectral");
    await userEvent.click(await screen.findByRole("link", { name: "Deep spectral unmixing" }));

    const back = await screen.findByRole("link", { name: /Back to library/ });
    expect(back).toHaveAttribute("href", "/research?search=spectral");
    await userEvent.click(back);
    expect(screen.getByTestId("url")).toHaveTextContent("/research?search=spectral");
    expect(screen.getByLabelText(/Search/)).toHaveValue("spectral");
  });

  it("links back to the plain library when opened directly", async () => {
    renderApp(`/research/papers/${PAPER_ID}`);
    expect(await screen.findByRole("link", { name: /Back to library/ })).toHaveAttribute("href", "/research");
  });

  it("asks for confirmation, deletes, and returns to the list", async () => {
    renderApp(`/research/papers/${PAPER_ID}`);
    await userEvent.click(await screen.findByRole("button", { name: "Delete paper" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Delete “Deep spectral unmixing”? This can't be undone.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(research.deletePaper).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Delete paper" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(screen.getByTestId("url")).toHaveTextContent(/^\/research$/));
    expect(research.deletePaper).toHaveBeenCalledWith(PAPER_ID);
    expect(await screen.findByText("Paper deleted.")).toBeInTheDocument();
  });

  it("shows the server's reason when the paper cannot be deleted", async () => {
    research.deletePaper.mockRejectedValue(
      Object.assign(new Error("403"), { isAxiosError: true, response: { status: 403, data: { detail: "This paper is used by a project." } } })
    );
    renderApp(`/research/papers/${PAPER_ID}`);
    await userEvent.click(await screen.findByRole("button", { name: "Delete paper" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("This paper is used by a project.")).toBeInTheDocument();
    expect(screen.getByTestId("url")).toHaveTextContent(`/research/papers/${PAPER_ID}`);
  });

  it("hides Delete from users who cannot edit, and the library link from guests", async () => {
    auth.getCurrentUser.mockResolvedValue(makeUser(["Guest"], GUEST_CAPS));
    research.getPaper.mockResolvedValue(paper({ can_edit: false }));
    renderApp(`/research/papers/${PAPER_ID}`);
    expect(await screen.findByRole("heading", { name: "Deep spectral unmixing" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete paper" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Back to library/ })).not.toBeInTheDocument();
  });
});

describe("Library list", () => {
  it("deletes a paper from its row after confirmation and refreshes", async () => {
    research.listPapers
      .mockResolvedValueOnce({ items: [paper(), paper({ id: "p2", title: "Read-only paper", can_edit: false })], total: 2, page: 1, page_size: 20 })
      .mockResolvedValue({ items: [paper({ id: "p2", title: "Read-only paper", can_edit: false })], total: 1, page: 1, page_size: 20 });
    renderApp("/research");

    await userEvent.click(await screen.findByRole("button", { name: "Delete Deep spectral unmixing" }));
    expect(screen.queryByRole("button", { name: "Delete Read-only paper" })).not.toBeInTheDocument();
    expect(screen.getByTestId("url")).toHaveTextContent(/^\/research$/); // the row click did not open the paper

    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.queryByRole("link", { name: "Deep spectral unmixing" })).not.toBeInTheDocument());
    expect(research.deletePaper).toHaveBeenCalledWith(PAPER_ID);
    expect(screen.getByText("Paper deleted.")).toBeInTheDocument();
  });
});
