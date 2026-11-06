import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as pdf from "../lib/pdfMetadata";
import { findIdentifiers } from "../lib/pdfMetadata";
import PaperFormModal from "../pages/research/PaperFormModal";
import * as authService from "../services/authService";
import * as researchService from "../services/researchService";
import { renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({ getCurrentUser: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn() }));
vi.mock("../services/researchService", () => ({ lookupDoi: vi.fn(), createPaper: vi.fn(), updatePaper: vi.fn() }));
vi.mock("../lib/pdfMetadata", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/pdfMetadata")>()),
  extractPdfMetadata: vi.fn(),
}));

const research = vi.mocked(researchService);
const reader = vi.mocked(pdf);

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

describe("Import from PDF", () => {
  it("fills the form from the PDF and DOI without uploading the file", async () => {
    reader.extractPdfMetadata.mockResolvedValue({ title: "draft title", authors: [], keywords: [], doi: null, arxivId: "1706.03762" });
    research.lookupDoi.mockResolvedValue({
      title: "Attention Is All You Need",
      authors: ["Ashish Vaswani", "Noam Shazeer"],
      abstract: "Transformers.",
      publication_year: 2017,
      venue: "NeurIPS",
      doi: "10.48550/arxiv.1706.03762",
      url: "https://doi.org/10.48550/arxiv.1706.03762",
      keywords: ["Machine Learning"],
      existing_paper_id: null,
    });
    research.createPaper.mockImplementation(async (input) => ({ id: "p1", ...input }) as never);
    const onSaved = vi.fn();

    renderWithProviders(<PaperFormModal open onClose={() => undefined} onSaved={onSaved} />);
    const file = new File(["%PDF-1.4"], "paper.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Import metadata from a PDF"), file);

    await waitFor(() => expect(screen.getByLabelText("Title")).toHaveValue("Attention Is All You Need"));
    expect(research.lookupDoi).toHaveBeenCalledWith("10.48550/arXiv.1706.03762");
    expect(screen.getByLabelText("Authors")).toHaveValue("Ashish Vaswani, Noam Shazeer");
    expect(screen.getByLabelText(/External URL/)).toHaveValue("https://arxiv.org/pdf/1706.03762");

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    // Only metadata is sent — never the file.
    const input = research.createPaper.mock.calls[0][0];
    expect(Object.values(input).some((value) => value instanceof File)).toBe(false);
    expect(input).toMatchObject({ title: "Attention Is All You Need", url: "https://arxiv.org/pdf/1706.03762", publication_year: 2017 });
  });

  it("warns when the paper is already in the library", async () => {
    reader.extractPdfMetadata.mockResolvedValue({ title: null, authors: [], keywords: [], doi: "10.1000/dup", arxivId: null });
    research.lookupDoi.mockResolvedValue({
      title: "Existing", authors: [], abstract: "", publication_year: null, venue: null,
      doi: "10.1000/dup", url: null, keywords: [], existing_paper_id: "abc",
    });
    renderWithProviders(<PaperFormModal open projectId="proj" onClose={() => undefined} onSaved={() => undefined} />);
    await userEvent.upload(screen.getByLabelText("Import metadata from a PDF"), new File(["x"], "a.pdf", { type: "application/pdf" }));
    expect(await screen.findByText(/already in the library/)).toBeInTheDocument();
  });
});
