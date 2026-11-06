import { useState, type FormEvent } from "react";

import { Alert, Button, Field, Input, Modal, Textarea } from "../../components/ui";
import { splitList } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { createPaper, updatePaper, type Paper } from "../../services/researchService";

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
        <Field label="External URL">{(id) => <Input id={id} type="url" value={url} onChange={(e) => setUrl(e.target.value)} />}</Field>
        <Field label="Keywords" hint="Separate keywords with commas.">
          {(id) => <Input id={id} value={keywords} onChange={(e) => setKeywords(e.target.value)} />}
        </Field>
        <div className="sm:col-span-2">
          <Field label="Abstract">{(id) => <Textarea id={id} rows={5} value={abstract} onChange={(e) => setAbstract(e.target.value)} />}</Field>
        </div>
        <p className="text-xs text-slate-500 sm:col-span-2">
          File uploads are not supported. Link to the publisher page, arXiv or DOI instead.
        </p>
        {error && (
          <div className="sm:col-span-2">
            <Alert>{error}</Alert>
          </div>
        )}
      </form>
    </Modal>
  );
}
