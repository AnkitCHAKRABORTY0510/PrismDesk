import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as pdf from "../lib/pdfMetadata";
import { findIdentifiers } from "../lib/pdfMetadata";
import PaperFormModal from "../pages/research/PaperFormModal";
import * as authService from "../services/authService";
import * as researchService from "../services/researchService";
import type { PaperLookup } from "../services/researchService";
import { renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({ getCurrentUser: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn() }));
vi.mock("../services/researchService", () => ({ lookupPaper: vi.fn(), createPaper: vi.fn(), updatePaper: vi.fn() }));
vi.mock("../lib/pdfMetadata", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/pdfMetadata")>()),
  extractPdfMetadata: vi.fn(),
}));

const research = vi.mocked(researchService);
const reader = vi.mocked(pdf);

const ATTENTION: PaperLookup = {
  title: "Attention Is All You Need",
  authors: ["Ashish Vaswani", "Noam Shazeer"],
  abstract: "Transformers.",
  publication_year: 2017,
  venue: "arXiv",
  doi: "10.48550/arxiv.1706.03762",
  url: "https://arxiv.org/abs/1706.03762",
  keywords: ["cs.CL", "cs.LG"],
  existing_paper_id: null,
  matched_by: "arxiv",
  source: "arxiv",
};

const renderForm = (props: { projectId?: string; onSaved?: () => void } = {}) =>
  renderWithProviders(<PaperFormModal open onClose={() => undefined} onSaved={props.onSaved ?? (() => undefined)} projectId={props.projectId} />);

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(authService).getCurrentUser.mockRejectedValue(new Error("anonymous"));
});

describe("findIdentifiers", () => {
  it("finds DOIs and arXiv IDs in PDF text", () => {
    expect(findIdentifiers("Published at doi: 10.1109/CVPR.2023.01234. Next")).toEqual({
      doi: "10.1109/CVPR.2023.01234",
      arxivId: null,
    });
    expect(findIdentifiers("arXiv:1706.03762v7 [cs.CL]").arxivId).toBe("1706.03762");
  });
});

describe("Quick add", () => {
  it("fetches on Enter, fills the form and marks auto-filled fields", async () => {
    research.lookupPaper.mockResolvedValue(ATTENTION);
    renderForm();

    await userEvent.type(screen.getByLabelText("Quick add"), "arXiv:1706.03762{Enter}");

    await waitFor(() => expect(screen.getByLabelText("Title")).toHaveValue("Attention Is All You Need"));
    expect(research.lookupPaper).toHaveBeenCalledWith("arXiv:1706.03762");
    expect(research.createPaper).not.toHaveBeenCalled(); // Enter did not submit the form
    expect(screen.getByLabelText("Authors")).toHaveValue("Ashish Vaswani, Noam Shazeer");
    expect(screen.getByLabelText("Publication year")).toHaveValue("2017");
    expect(screen.getByLabelText("DOI")).toHaveValue("10.48550/arxiv.1706.03762");
    expect(screen.getByLabelText("Keywords")).toHaveValue("cs.CL, cs.LG");
    expect(screen.getByLabelText("Abstract")).toHaveValue("Transformers.");
    expect(screen.getAllByText(/Auto-filled/)).toHaveLength(8);
    expect(screen.getByText(/Filled title, authors.*from arXiv/)).toBeInTheDocument();

    // Fields stay editable, and editing clears the auto-filled mark.
    await userEvent.clear(screen.getByLabelText("Title"));
    await userEvent.type(screen.getByLabelText("Title"), "My title");
    expect(screen.getByLabelText("Title")).toHaveValue("My title");
    expect(screen.getAllByText(/Auto-filled/)).toHaveLength(7);
  });

  it("keeps fields the user typed and fills the empty ones", async () => {
    research.lookupPaper.mockResolvedValue(ATTENTION);
    renderForm();

    await userEvent.type(screen.getByLabelText("Title"), "Handwritten title");
    await userEvent.type(screen.getByLabelText("Quick add"), "1706.03762");
    await userEvent.click(screen.getByRole("button", { name: "Fetch" }));

    await waitFor(() => expect(screen.getByLabelText("Authors")).toHaveValue("Ashish Vaswani, Noam Shazeer"));
    expect(screen.getByLabelText("Title")).toHaveValue("Handwritten title");
  });

  it("shows a loading state and the error when nothing is found", async () => {
    let reject: (error: unknown) => void = () => undefined;
    research.lookupPaper.mockReturnValue(new Promise((_, r) => (reject = r)));
    renderForm();

    await userEvent.type(screen.getByLabelText("Quick add"), "10.1000/missing");
    await userEvent.click(screen.getByRole("button", { name: "Fetch" }));
    expect(screen.getByRole("button", { name: "Fetching…" })).toBeDisabled();

    reject(Object.assign(new Error("404"), { isAxiosError: true, response: { status: 404, data: { detail: "No metadata was found for this DOI." } } }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No metadata was found for this DOI.");
    expect(screen.getByLabelText("Title")).toHaveValue("");
  });

  it("warns about a duplicate with a link to the existing paper", async () => {
    research.lookupPaper.mockResolvedValue({ ...ATTENTION, existing_paper_id: "abc" });
    renderForm({ projectId: "proj" });

    await userEvent.type(screen.getByLabelText("Quick add"), "1706.03762{Enter}");
    expect(await screen.findByText(/already in the library/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open it" })).toHaveAttribute("href", "/research/papers/abc");
  });

  it("flags a title search as a best match", async () => {
    research.lookupPaper.mockResolvedValue({ ...ATTENTION, matched_by: "title", source: "crossref" });
    renderForm();
    await userEvent.type(screen.getByLabelText("Quick add"), "attention is all you need{Enter}");
    expect(await screen.findByText(/closest title match/)).toBeInTheDocument();
  });
});

describe("Import from PDF", () => {
  it("looks up the arXiv ID found in the PDF and saves only metadata", async () => {
    reader.extractPdfMetadata.mockResolvedValue({ title: "draft title", authors: [], keywords: [], doi: null, arxivId: "1706.03762" });
    research.lookupPaper.mockResolvedValue(ATTENTION);
    research.createPaper.mockImplementation(async (input) => ({ id: "p1", ...input }) as never);
    const onSaved = vi.fn();
    renderForm({ onSaved });

    const file = new File(["%PDF-1.4"], "paper.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Import metadata from a PDF"), file);

    await waitFor(() => expect(screen.getByLabelText("Title")).toHaveValue("Attention Is All You Need"));
    expect(research.lookupPaper).toHaveBeenCalledWith("arXiv:1706.03762");
    expect(screen.getByLabelText("Quick add")).toHaveValue("arXiv:1706.03762");

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const input = research.createPaper.mock.calls[0][0];
    expect(Object.values(input).some((value) => value instanceof File)).toBe(false);
    expect(input).toMatchObject({ title: "Attention Is All You Need", url: "https://arxiv.org/abs/1706.03762", publication_year: 2017 });
  });

  it("offers a title search when the PDF has no identifier", async () => {
    reader.extractPdfMetadata.mockResolvedValue({ title: "A PDF title", authors: ["Mia K"], keywords: [], doi: null, arxivId: null });
    renderForm();
    await userEvent.upload(screen.getByLabelText("Import metadata from a PDF"), new File(["x"], "a.pdf", { type: "application/pdf" }));

    expect(await screen.findByText(/press Fetch to search by title/)).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue("A PDF title");
    expect(screen.getByLabelText("Quick add")).toHaveValue("A PDF title");
    expect(research.lookupPaper).not.toHaveBeenCalled();
  });
});
