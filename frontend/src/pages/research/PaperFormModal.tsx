import { useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent } from "react";

import { Link } from "react-router";

import { Alert, Button, Field, Input, Modal, Textarea } from "../../components/ui";
import { splitList } from "../../lib/format";
import { extractPdfMetadata } from "../../lib/pdfMetadata";
import { getErrorMessage } from "../../services/api";
import { createPaper, lookupPaper, updatePaper, type Paper, type PaperLookup } from "../../services/researchService";

type FieldKey = "title" | "authors" | "year" | "venue" | "doi" | "url" | "keywords" | "abstract";
type FormValues = Record<FieldKey, string>;

const FIELD_NAMES: Record<FieldKey, string> = {
  title: "title",
  authors: "authors",
  year: "year",
  venue: "venue",
  doi: "DOI",
  url: "URL",
  keywords: "keywords",
  abstract: "abstract",
};

const SOURCE_NAMES: Record<string, string> = {
  crossref: "Crossref",
  arxiv: "arXiv",
  "doi.org": "doi.org",
  webpage: "the web page",
};

function describeSource(source: string | null): string {
  if (!source) return "the lookup";
  return source
    .split("+")
    .map((part) => SOURCE_NAMES[part] ?? part)
    .join(" and ");
}

function lookupToValues(meta: PaperLookup): Partial<FormValues> {
  return {
    title: meta.title ?? "",
    authors: meta.authors.join(", "),
    year: meta.publication_year?.toString() ?? "",
    venue: meta.venue ?? "",
    doi: meta.doi ?? "",
    url: meta.url ?? "",
    keywords: meta.keywords.join(", "),
    abstract: meta.abstract,
  };
}

const AUTO_HINT = "Auto-filled — check before saving.";

// Paper metadata only: Prism Desk never uploads or stores paper files.
export default function PaperFormModal({
  open,
  paper,
  projectId,
  onClose,
  onSaved,
}: {
  open: boolean;
  paper?: Paper | null;
  projectId?: string;
  onClose: () => void;
  onSaved: (paper: Paper) => void;
}) {
  const [values, setValues] = useState<FormValues>({
    title: paper?.title ?? "",
    authors: paper?.authors.join(", ") ?? "",
    year: paper?.publication_year?.toString() ?? "",
    venue: paper?.venue ?? "",
    doi: paper?.doi ?? "",
    url: paper?.url ?? "",
    keywords: paper?.keywords.join(", ") ?? "",
    abstract: paper?.abstract ?? "",
  });
  // Latest values for async handlers (a lookup may finish after more typing).
  // Every change goes through edit() or fill(), which keep it in sync.
  const valuesRef = useRef(values);
  // Fields the user typed into; a lookup never overwrites these unless they are empty.
  const editedRef = useRef(new Set<FieldKey>(paper ? (Object.keys(FIELD_NAMES) as FieldKey[]) : []));
  const [autoFilled, setAutoFilled] = useState<Set<FieldKey>>(new Set());

  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [lookupError, setLookupError] = useState("");
  const [saving, setSaving] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importInfo, setImportInfo] = useState("");
  const [existingId, setExistingId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const edit = (key: FieldKey) => (value: string) => {
    editedRef.current.add(key);
    setAutoFilled((current) => {
      if (!current.has(key)) return current;
      const next = new Set(current);
      next.delete(key);
      return next;
    });
    const next = { ...valuesRef.current, [key]: value };
    valuesRef.current = next;
    setValues(next);
  };

  /** Fill fields that are empty or were not typed by the user. Returns the filled keys. */
  const fill = (incoming: Partial<FormValues>): FieldKey[] => {
    const current = valuesRef.current;
    const filled: FieldKey[] = [];
    const next = { ...current };
    for (const [key, value] of Object.entries(incoming) as [FieldKey, string | undefined][]) {
      if (!value || value === current[key]) continue;
      if (current[key].trim() && editedRef.current.has(key)) continue;
      next[key] = value;
      filled.push(key);
    }
    if (filled.length) {
      valuesRef.current = next;
      setValues(next);
      setAutoFilled((previous) => new Set([...previous, ...filled]));
    }
    return filled;
  };

  const applyLookup = (meta: PaperLookup, prefix = ""): void => {
    const filled = fill(lookupToValues(meta));
    setExistingId(meta.existing_paper_id);
    const source = describeSource(meta.source);
    const what = filled.length
      ? `Filled ${filled.map((key) => FIELD_NAMES[key]).join(", ")} from ${source}.`
      : `Nothing new was found on ${source} — fields you edited were kept.`;
    const caution = meta.matched_by === "title" ? " This is the closest title match — make sure it is the right paper." : "";
    setImportInfo(`${prefix}${what}${caution} Review everything before saving.`);
  };

  const runLookup = async (raw: string) => {
    const value = raw.trim();
    if (!value || fetching) return;
    setLookupError("");
    setImportInfo("");
    setFetching(true);
    try {
      applyLookup(await lookupPaper(value));
    } catch (err) {
      setLookupError(getErrorMessage(err));
    } finally {
      setFetching(false);
    }
  };

  const onQueryKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      // Enter fetches metadata instead of submitting the paper form.
      event.preventDefault();
      void runLookup(query);
    }
  };

  const importPdf = async (file: File | undefined) => {
    if (!file) return;
    if (file.type && file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setLookupError("Only PDF files can be read.");
      return;
    }
    setLookupError("");
    setImportInfo("");
    setImporting(true);
    try {
      const meta = await extractPdfMetadata(file);
      fill({
        title: meta.title ?? "",
        authors: meta.authors.join(", "),
        keywords: meta.keywords.join(", "),
      });
      const identifier = meta.doi ?? (meta.arxivId ? `arXiv:${meta.arxivId}` : null);
      if (identifier) {
        setQuery(identifier);
        try {
          applyLookup(await lookupPaper(identifier), `Found ${identifier} in the PDF. `);
        } catch (err) {
          fill({ doi: meta.doi ?? "" });
          setLookupError(`Found ${identifier} in the PDF, but could not fetch its details: ${getErrorMessage(err)}`);
        }
      } else {
        if (meta.title) setQuery(meta.title);
        setImportInfo(
          meta.title
            ? "No DOI or arXiv ID was found in the PDF. Title and authors were read from the file — press Fetch to search by title."
            : "No DOI or arXiv ID was found in the PDF. Paste the DOI or a link above, or fill in the fields manually."
        );
      }
    } catch {
      setLookupError("This PDF could not be read. Paste its DOI or link instead, or enter the details manually.");
    } finally {
      setImporting(false);
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void importPdf(event.dataTransfer.files?.[0]);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (values.year && !/^\d{4}$/.test(values.year)) {
      setError("Publication year must be a four-digit year.");
      return;
    }
    if (values.url && !/^https?:\/\//i.test(values.url)) {
      setError("The paper URL must start with http:// or https://.");
      return;
    }
    const input = {
      title: values.title.trim(),
      authors: splitList(values.authors),
      abstract: values.abstract,
      publication_year: values.year ? Number(values.year) : null,
      venue: values.venue.trim() || null,
      doi: values.doi.trim() || null,
      url: values.url.trim() || null,
      keywords: splitList(values.keywords),
    };
    setSaving(true);
    try {
      const saved = paper
        ? await updatePaper(paper.id, input)
        : await createPaper({ ...input, project_id: projectId ?? null });
      onSaved(saved);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const hint = (key: FieldKey, normal?: string) => (autoFilled.has(key) ? AUTO_HINT : normal);
  const busy = fetching || importing;

  return (
    <Modal
      open={open}
      wide
      title={paper ? "Edit paper metadata" : "Add research paper"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="paper-form" loading={saving}>
            Save
          </Button>
        </>
      }
    >
      <form id="paper-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {!paper && (
          <div
            className={`space-y-3 rounded-lg border border-dashed p-4 sm:col-span-2 ${dragging ? "border-ring bg-surface" : "border-line-strong bg-surface-muted"}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <Field label="Quick add" hint="DOI, arXiv ID or link, a journal/publisher page, or a paper title. You can also drop a PDF here.">
              {(id) => (
                <div className="flex flex-wrap gap-2">
                  <Input
                    id={id}
                    className="flex-1 basis-60"
                    placeholder="Paste DOI, arXiv ID or link"
                    value={query}
                    disabled={importing}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={onQueryKey}
                  />
                  <Button onClick={() => void runLookup(query)} disabled={!query.trim() || busy}>
                    {fetching ? "Fetching…" : "Fetch"}
                  </Button>
                  <Button variant="secondary" disabled={busy} onClick={() => fileInput.current?.click()}>
                    {importing ? "Reading PDF…" : "Import from PDF"}
                  </Button>
                  <input
                    ref={fileInput}
                    type="file"
                    accept="application/pdf"
                    className="sr-only"
                    tabIndex={-1}
                    aria-label="Import metadata from a PDF"
                    disabled={busy}
                    onChange={(event) => {
                      void importPdf(event.target.files?.[0]);
                      event.target.value = "";
                    }}
                  />
                </div>
              )}
            </Field>
            <p className="text-xs text-fg-muted">
              A PDF is read in your browser only to find its DOI or arXiv ID. It is not uploaded or stored —
              add a download link (publisher, arXiv or lab Drive) in “External URL”.
            </p>
            {lookupError && <Alert>{lookupError}</Alert>}
            {importInfo && <Alert kind="info">{importInfo}</Alert>}
            {existingId && (
              <Alert kind="info">
                This paper is already in the library.{" "}
                <Link to={`/research/papers/${existingId}`} className="underline">Open it</Link>
                {projectId ? " — saving will link it to this project instead of creating a duplicate." : "."}
              </Alert>
            )}
          </div>
        )}
        <div className="sm:col-span-2">
          <Field label="Title" hint={hint("title")}>
            {(id) => <Input id={id} value={values.title} required maxLength={500} onChange={(e) => edit("title")(e.target.value)} />}
          </Field>
        </div>
        <Field label="Authors" hint={hint("authors", "Separate names with commas.")}>
          {(id) => <Input id={id} value={values.authors} onChange={(e) => edit("authors")(e.target.value)} />}
        </Field>
        <Field label="Publication year" hint={hint("year")}>
          {(id) => <Input id={id} inputMode="numeric" value={values.year} onChange={(e) => edit("year")(e.target.value)} />}
        </Field>
        <Field label="Journal or conference" hint={hint("venue")}>
          {(id) => <Input id={id} value={values.venue} onChange={(e) => edit("venue")(e.target.value)} />}
        </Field>
        <Field label="DOI" hint={hint("doi", "For example 10.1109/CVPR.2023.01234 — duplicates are detected.")}>
          {(id) => <Input id={id} value={values.doi} onChange={(e) => edit("doi")(e.target.value)} />}
        </Field>
        <Field label="External URL (download link)" hint={hint("url", "Where lab members can open or download the paper.")}>
          {(id) => <Input id={id} type="url" value={values.url} onChange={(e) => edit("url")(e.target.value)} />}
        </Field>
        <Field label="Keywords" hint={hint("keywords", "Separate keywords with commas.")}>
          {(id) => <Input id={id} value={values.keywords} onChange={(e) => edit("keywords")(e.target.value)} />}
        </Field>
        <div className="sm:col-span-2">
          <Field label="Abstract" hint={hint("abstract")}>
            {(id) => <Textarea id={id} rows={5} value={values.abstract} onChange={(e) => edit("abstract")(e.target.value)} />}
          </Field>
        </div>
        {error && (
          <div className="sm:col-span-2">
            <Alert>{error}</Alert>
          </div>
        )}
      </form>
    </Modal>
  );
}
