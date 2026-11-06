import { useState, type FormEvent } from "react";

import { Link } from "react-router";

import { Alert, Button, Field, Input, Modal, Textarea } from "../../components/ui";
import { splitList } from "../../lib/format";
import { extractPdfMetadata } from "../../lib/pdfMetadata";
import { getErrorMessage } from "../../services/api";
import { createPaper, lookupDoi, updatePaper, type Paper } from "../../services/researchService";

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
  const [title, setTitle] = useState(paper?.title ?? "");
  const [authors, setAuthors] = useState(paper?.authors.join(", ") ?? "");
  const [year, setYear] = useState(paper?.publication_year?.toString() ?? "");
  const [venue, setVenue] = useState(paper?.venue ?? "");
  const [doi, setDoi] = useState(paper?.doi ?? "");
  const [url, setUrl] = useState(paper?.url ?? "");
  const [keywords, setKeywords] = useState(paper?.keywords.join(", ") ?? "");
  const [abstract, setAbstract] = useState(paper?.abstract ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importInfo, setImportInfo] = useState("");
  const [existingId, setExistingId] = useState<string | null>(null);

  // Fill empty fields from doi.org; the user reviews everything before saving.
  const applyDoi = async (value: string, overwrite: boolean) => {
    const meta = await lookupDoi(value);
    const pick = (current: string, next: string | null | undefined) => (overwrite || !current ? next ?? current : current);
    setDoi(meta.doi);
    setTitle((t) => pick(t, meta.title));
    setAuthors((a) => pick(a, meta.authors.join(", ")));
    setYear((y) => pick(y, meta.publication_year?.toString()));
    setVenue((v) => pick(v, meta.venue));
    setKeywords((k) => pick(k, meta.keywords.join(", ")));
    setAbstract((a) => pick(a, meta.abstract));
    setUrl((u) => u || meta.url || "");
    setExistingId(meta.existing_paper_id);
  };

  const importPdf = async (file: File | undefined) => {
    if (!file) return;
    setError("");
    setImportInfo("");
    setImporting(true);
    try {
      const meta = await extractPdfMetadata(file);
      if (meta.title) setTitle(meta.title);
      if (meta.authors.length) setAuthors(meta.authors.join(", "));
      if (meta.keywords.length) setKeywords(meta.keywords.join(", "));
      const found = meta.doi ?? (meta.arxivId ? `10.48550/arXiv.${meta.arxivId}` : null);
      if (meta.arxivId) setUrl(`https://arxiv.org/pdf/${meta.arxivId}`);
      if (found) {
        try {
          await applyDoi(found, true);
          setImportInfo(`Filled from the PDF and DOI ${found}. Check the fields before saving.`);
        } catch {
          setDoi(found);
          setImportInfo(`Found DOI ${found} in the PDF, but could not fetch its metadata. Fill in the rest manually.`);
        }
      } else {
        setImportInfo("No DOI was found in the PDF. Title and authors were read from the file where available.");
      }
    } catch {
      setError("This PDF could not be read. Enter the details manually.");
    } finally {
      setImporting(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (year && !/^\d{4}$/.test(year)) {
      setError("Publication year must be a four-digit year.");
      return;
    }
    if (url && !/^https?:\/\//i.test(url)) {
      setError("The paper URL must start with http:// or https://.");
      return;
    }
    const input = {
      title: title.trim(),
      authors: splitList(authors),
      abstract,
      publication_year: year ? Number(year) : null,
      venue: venue.trim() || null,
      doi: doi.trim() || null,
      url: url.trim() || null,
      keywords: splitList(keywords),
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
          <div className="space-y-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 sm:col-span-2">
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex cursor-pointer items-center rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover">
                {importing ? "Reading PDF…" : "Import from PDF"}
                <input
                  type="file"
                  accept="application/pdf"
                  className="sr-only"
                  aria-label="Import metadata from a PDF"
                  disabled={importing}
                  onChange={(event) => {
                    void importPdf(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
              </label>
              <Button
                variant="secondary"
                disabled={!doi.trim() || importing}
                onClick={async () => {
                  setError("");
                  try {
                    await applyDoi(doi.trim(), false);
                    setImportInfo("Empty fields were filled from doi.org.");
                  } catch (err) {
                    setError(getErrorMessage(err));
                  }
                }}
              >
                Look up DOI
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              The PDF is read in your browser only to extract its metadata. It is not uploaded or stored —
              add a download link (publisher, arXiv or lab Drive) in “External URL”.
            </p>
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
          <Field label="Title">{(id) => <Input id={id} value={title} required maxLength={500} onChange={(e) => setTitle(e.target.value)} />}</Field>
        </div>
        <Field label="Authors" hint="Separate names with commas.">
          {(id) => <Input id={id} value={authors} onChange={(e) => setAuthors(e.target.value)} />}
        </Field>
        <Field label="Publication year">{(id) => <Input id={id} inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value)} />}</Field>
        <Field label="Journal or conference">{(id) => <Input id={id} value={venue} onChange={(e) => setVenue(e.target.value)} />}</Field>
        <Field label="DOI" hint="For example 10.1109/CVPR.2023.01234 — duplicates are detected.">
          {(id) => <Input id={id} value={doi} onChange={(e) => setDoi(e.target.value)} />}
        </Field>
        <Field label="External URL (download link)" hint="Where lab members can open or download the paper.">
          {(id) => <Input id={id} type="url" value={url} onChange={(e) => setUrl(e.target.value)} />}
        </Field>
        <Field label="Keywords" hint="Separate keywords with commas.">
          {(id) => <Input id={id} value={keywords} onChange={(e) => setKeywords(e.target.value)} />}
        </Field>
        <div className="sm:col-span-2">
          <Field label="Abstract">{(id) => <Textarea id={id} rows={5} value={abstract} onChange={(e) => setAbstract(e.target.value)} />}</Field>
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
