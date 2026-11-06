import { useState, type FormEvent } from "react";

import { Alert, Button, Field, Input, Modal, Select, Textarea } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { splitList, todayLocal } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { createEntry, updateEntry, type HandbookEntry } from "../../services/handbookService";
import { listProjects } from "../../services/projectService";

export default function EntryFormModal({
  open,
  entry,
  projectId,
  onClose,
  onSaved,
}: {
  open: boolean;
  entry?: HandbookEntry | null;
  projectId?: string;
  onClose: () => void;
  onSaved: (entry: HandbookEntry) => void;
}) {
  const projects = useAsync(() => listProjects({ mine: true, status: "active", page_size: 100 }), []);
  const [project, setProject] = useState(entry?.project_id ?? projectId ?? "");
  const [date, setDate] = useState(entry?.entry_date ?? todayLocal());
  const [work, setWork] = useState(entry?.work_completed ?? "");
  const [progress, setProgress] = useState(entry?.research_progress ?? "");
  const [problems, setProblems] = useState(entry?.problems ?? "");
  const [next, setNext] = useState(entry?.next_steps ?? "");
  const [references, setReferences] = useState(entry?.references.join("\n") ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const writable = (projects.data?.items ?? []).filter((p) => p.my_role === "owner" || p.my_role === "member");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (![work, progress, problems, next].some((value) => value.trim())) {
      setError("Describe at least one part of the day's work.");
      return;
    }
    const fields = {
      work_completed: work,
      research_progress: progress,
      problems,
      next_steps: next,
      references: splitList(references),
    };
    setSaving(true);
    try {
      const saved = entry
        ? await updateEntry(entry.id, fields)
        : await createEntry({ ...fields, project_id: project, entry_date: date });
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
                <Select id={id} value={project} required onChange={(e) => setProject(e.target.value)}>
                  <option value="">Select a project…</option>
                  {writable.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Entry date" hint="One entry per project per day.">
              {(id) => <Input id={id} type="date" value={date} max={todayLocal()} required onChange={(e) => setDate(e.target.value)} />}
            </Field>
          </>
        )}
        <Field label="Work completed">{(id) => <Textarea id={id} value={work} onChange={(e) => setWork(e.target.value)} />}</Field>
        <Field label="Research progress">{(id) => <Textarea id={id} value={progress} onChange={(e) => setProgress(e.target.value)} />}</Field>
        <Field label="Problems encountered">{(id) => <Textarea id={id} value={problems} onChange={(e) => setProblems(e.target.value)} />}</Field>
        <Field label="Next steps">{(id) => <Textarea id={id} value={next} onChange={(e) => setNext(e.target.value)} />}</Field>
        <div className="sm:col-span-2">
          <Field label="References / external links" hint="One URL per line.">
            {(id) => <Textarea id={id} rows={2} value={references} onChange={(e) => setReferences(e.target.value)} />}
          </Field>
        </div>
        {entry && <p className="text-xs text-slate-500 sm:col-span-2">Saving creates version {entry.version + 1}; earlier versions stay in the history.</p>}
        {error && <div className="sm:col-span-2"><Alert>{error}</Alert></div>}
      </form>
    </Modal>
  );
}
