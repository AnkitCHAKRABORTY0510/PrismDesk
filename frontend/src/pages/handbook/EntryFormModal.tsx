import { useState, type FormEvent } from "react";

import { Alert, Button, Field, Input, Modal, Select, Textarea } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { todayLocal } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { createEntry, updateEntry, type HandbookEntry } from "../../services/handbookService";
import { listProjects } from "../../services/projectService";
import { parseReferences, readStorage, writeStorage } from "./plannerMeta";

const LAST_PROJECT_KEY = "prismdesk.handbook.lastProject";

export default function EntryFormModal({
  open,
  entry,
  projectId,
  defaultDate,
  onClose,
  onSaved,
}: {
  open: boolean;
  entry?: HandbookEntry | null;
  projectId?: string;
  defaultDate?: string;
  onClose: () => void;
  onSaved: (entry: HandbookEntry) => void;
}) {
  const projects = useAsync(() => listProjects({ mine: true, status: "active", page_size: 100 }), []);
  const [project, setProject] = useState(entry?.project_id ?? projectId ?? readStorage(LAST_PROJECT_KEY) ?? "");
  const [date, setDate] = useState(entry?.entry_date ?? defaultDate ?? todayLocal());
  const [work, setWork] = useState(entry?.work_completed ?? "");
  const [progress, setProgress] = useState(entry?.research_progress ?? "");
  const [problems, setProblems] = useState(entry?.problems ?? "");
  const [next, setNext] = useState(entry?.next_steps ?? "");
  const [references, setReferences] = useState(entry?.references.join("\n") ?? "");
  const [error, setError] = useState("");
  const [referenceError, setReferenceError] = useState("");
  const [saving, setSaving] = useState(false);

  const writable = (projects.data?.items ?? []).filter((p) => p.my_role === "owner" || p.my_role === "member");
  // A remembered project the user can no longer write to is not offered.
  const projectValue = projects.data && !entry && !projectId && project && !writable.some((p) => p.id === project) ? "" : project;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (![work, progress, problems, next].some((value) => value.trim())) {
      setError("Describe at least one part of the day's work.");
      return;
    }
    const refs = parseReferences(references);
    setReferenceError(refs.error);
    if (refs.error) return;
    const fields = {
      work_completed: work,
      research_progress: progress,
      problems,
      next_steps: next,
      references: refs.urls,
    };
    setSaving(true);
    try {
      const saved = entry
        ? await updateEntry(entry.id, fields)
        : await createEntry({ ...fields, project_id: projectValue, entry_date: date });
      if (!entry) writeStorage(LAST_PROJECT_KEY, projectValue);
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
      title={entry ? `Edit entry for ${entry.entry_date}` : "New project-wise daily entry"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="entry-form" loading={saving}>Save entry</Button>
        </>
      }
    >
      <form id="entry-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {!entry && (
          <>
            <Field label="Project">
              {(id) => (
                <Select id={id} value={projectValue} required onChange={(e) => setProject(e.target.value)}>
                  <option value="">Select a project…</option>
                  {writable.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Entry date" hint="One entry per project per day; not in the future.">
              {(id) => <Input id={id} type="date" value={date} max={todayLocal()} required onChange={(e) => setDate(e.target.value)} />}
            </Field>
          </>
        )}
        <Field label="Work completed">{(id) => <Textarea id={id} value={work} onChange={(e) => setWork(e.target.value)} />}</Field>
        <Field label="Research progress">{(id) => <Textarea id={id} value={progress} onChange={(e) => setProgress(e.target.value)} />}</Field>
        <Field label="Problems encountered">{(id) => <Textarea id={id} value={problems} onChange={(e) => setProblems(e.target.value)} />}</Field>
        <Field label="Next steps">{(id) => <Textarea id={id} value={next} onChange={(e) => setNext(e.target.value)} />}</Field>
        <div className="sm:col-span-2">
          <Field label="References / external links" hint="One URL per line." error={referenceError}>
            {(id) => <Textarea id={id} rows={2} value={references} placeholder="https://arxiv.org/abs/…" onChange={(e) => { setReferences(e.target.value); setReferenceError(""); }} />}
          </Field>
        </div>
        {entry && <p className="text-xs text-fg-muted sm:col-span-2">Saving creates version {entry.version + 1}; earlier versions stay in the history.</p>}
        {error && <div className="sm:col-span-2"><Alert>{error}</Alert></div>}
      </form>
    </Modal>
  );
}
