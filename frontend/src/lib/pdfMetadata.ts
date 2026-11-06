// Read paper metadata from a PDF entirely in the browser. The file is
// never sent to the server and nothing is stored: only the extracted
// text fields are used to pre-fill the paper form.

export interface PdfMetadata {
  title: string | null;
  authors: string[];
  keywords: string[];
  doi: string | null;
  arxivId: string | null;
}

const DOI_PATTERN = /\b(10\.\d{4,9}\/[^\s"<>{}]+)/i;
const ARXIV_PATTERN = /arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?/i;

export function findIdentifiers(text: string): { doi: string | null; arxivId: string | null } {
  const doiMatch = text.match(DOI_PATTERN);
  // Strip trailing punctuation that often follows a DOI in running text.
  const doi = doiMatch ? doiMatch[1].replace(/[.,;)\]]+$/, "") : null;
  const arxiv = text.match(ARXIV_PATTERN);
  return { doi, arxivId: arxiv ? arxiv[1] : null };
}

function splitPeople(value: string): string[] {
  return value
    .split(/;|,| and /)
    .map((item) => item.trim())
    .filter((item) => item.length > 1);
}

export async function extractPdfMetadata(file: File): Promise<PdfMetadata> {
  // Loaded on demand so pdf.js does not weigh down every page.
  const pdfjs = await import("pdfjs-dist");
  const workerUrl = (await import("pdfjs-dist/build/pdf.worker.min.mjs?url")).default;
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

  const data = new Uint8Array(await file.arrayBuffer());
  const pdf = await pdfjs.getDocument({ data }).promise;

  try {
    const info = (await pdf.getMetadata()).info as unknown as Record<string, unknown>;
    const text = (key: string) => (typeof info?.[key] === "string" ? (info[key] as string).trim() : "");

    // DOIs and arXiv IDs are normally printed on the first pages.
    let firstPages = "";
    for (let page = 1; page <= Math.min(pdf.numPages, 2); page += 1) {
      const content = await (await pdf.getPage(page)).getTextContent();
      firstPages += " " + content.items.map((item) => ("str" in item ? item.str : "")).join(" ");
    }

    const ids = findIdentifiers(`${text("Subject")} ${text("Keywords")} ${firstPages}`);
    return {
      title: text("Title") || null,
      authors: text("Author") ? splitPeople(text("Author")) : [],
      keywords: text("Keywords") ? text("Keywords").split(/[;,]/).map((k) => k.trim()).filter(Boolean) : [],
      doi: ids.doi,
      arxivId: ids.arxivId,
    };
  } finally {
    await pdf.destroy();
  }
}
