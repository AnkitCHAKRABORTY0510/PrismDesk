import { useState, type FormEvent } from "react";

import { Alert, Button, Field, Input, Modal, Select, Textarea } from "../../components/ui";
import { isoToLocalInput, localInputToIso } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { createJournal, updateJournal, type Journal, type Quartile } from "../../services/journalService";

export default function JournalFormModal({
  open,
  journal,
  onClose,
  onSaved,
}: {
  open: boolean;
  journal?: Journal | null;
  onClose: () => void;
  onSaved: (journal: Journal) => void;
}) {
  const [title, setTitle] = useState(journal?.title ?? "");
  const [issn, setIssn] = useState(journal?.issn ?? "");
  const [publisher, setPublisher] = useState(journal?.publisher ?? "");
  const [homepage, setHomepage] = useState(journal?.homepage_url ?? "");
  const [quartile, setQuartile] = useState<string>(journal?.sjr_quartile ?? "");
  const [openAccess, setOpenAccess] = useState(journal?.is_open_access ?? false);
  const [specialIssue, setSpecialIssue] = useState(journal?.special_issue_title ?? "");
  const [deadline, setDeadline] = useState(isoToLocalInput(journal?.submission_deadline));
  const [notes, setNotes] = useState(journal?.notes ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    const input = {
      title,
      issn: issn.trim() || null,
      publisher: publisher.trim() || null,
      homepage_url: homepage.trim() || null,
      sjr_quartile: (quartile || null) as Quartile | null,
      is_open_access: openAccess,
      notes,
      special_issue_title: specialIssue.trim() || null,
      submission_deadline: deadline ? localInputToIso(deadline) : null,
    };
    setSaving(true);
    try {
      onSaved(journal ? await updateJournal(journal.id, input) : await createJournal(input));
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
      title={journal ? "Edit journal" : "Add journal"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="journal-form" loading={saving}>Save</Button>
        </>
      }
    >
      <form id="journal-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Field label="Journal title">{(id) => <Input id={id} required value={title} onChange={(e) => setTitle(e.target.value)} />}</Field>
        </div>
        <Field label="ISSN" hint="e.g. 1532-4435">{(id) => <Input id={id} value={issn} onChange={(e) => setIssn(e.target.value)} />}</Field>
        <Field label="Publisher">{(id) => <Input id={id} value={publisher} onChange={(e) => setPublisher(e.target.value)} />}</Field>
        <Field label="Homepage">{(id) => <Input id={id} type="url" value={homepage} onChange={(e) => setHomepage(e.target.value)} />}</Field>
        <Field label="SJR quartile">
          {(id) => (
            <Select id={id} value={quartile} onChange={(e) => setQuartile(e.target.value)}>
              <option value="">Not set</option>
              {["Q1", "Q2", "Q3", "Q4"].map((q) => (
                <option key={q} value={q}>{q}</option>
              ))}
            </Select>
          )}
        </Field>
        <label className="flex items-center gap-2 text-sm text-fg-soft sm:col-span-2">
          <input type="checkbox" className="h-4 w-4 rounded border-line-strong accent-[var(--primary)]" checked={openAccess} onChange={(e) => setOpenAccess(e.target.checked)} />
          Open access journal
        </label>
        <fieldset className="grid gap-4 rounded-lg border border-line p-3 sm:col-span-2 sm:grid-cols-2">
          <legend className="px-1 text-sm font-medium text-fg-soft">Special issue (optional)</legend>
          <p className="text-xs text-fg-muted sm:col-span-2">
            Leave empty for regular, year-round submissions. Add a special issue to track its deadline with a countdown.
          </p>
          <Field label="Special issue name">{(id) => <Input id={id} value={specialIssue} onChange={(e) => setSpecialIssue(e.target.value)} />}</Field>
          <Field label="Submission deadline" hint="Your local time; stored in UTC.">
            {(id) => <Input id={id} type="datetime-local" value={deadline} onChange={(e) => setDeadline(e.target.value)} />}
          </Field>
        </fieldset>
        <div className="sm:col-span-2">
          <Field label="Notes">{(id) => <Textarea id={id} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />}</Field>
        </div>
        {error && <div className="sm:col-span-2"><Alert>{error}</Alert></div>}
      </form>
    </Modal>
  );
}
