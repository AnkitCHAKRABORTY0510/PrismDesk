import { useState, type FormEvent } from "react";
import { BellRing } from "lucide-react";

import { Alert, Button, Field, Input, Loading, Modal, Select, Textarea } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { humanize, localInputToIso } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import { listProjects } from "../../services/projectService";
import { createTask, listTasks, reminderRecipients, type Task } from "../../services/taskService";

/**
 * Send a reminder to other users. Professors/administrators can remind any
 * active member of a project they supervise (optionally about one task).
 * Students can only remind the project's professors, about a task assigned
 * to them. Recipients get a private Discord message; the server enforces
 * the same rules.
 */
export default function ReminderFormModal({
  open,
  relatedTask,
  defaultRecipientIds = [],
  onClose,
  onSent,
}: {
  open: boolean;
  /** Fixes the reminder to this official task (and its project). */
  relatedTask?: Task | null;
  defaultRecipientIds?: string[];
  onClose: () => void;
  onSent: (reminder: Task) => void;
}) {
  const { user } = useAuth();
  const manager = can(user, "tasks.review");
  const [projectId, setProjectId] = useState(relatedTask?.project_id ?? "");
  const [taskId, setTaskId] = useState(relatedTask?.id ?? "");
  const [recipients, setRecipients] = useState<string[]>(defaultRecipientIds);
  const [title, setTitle] = useState(
    relatedTask ? (manager ? `Reminder: ${relatedTask.title}` : `Please check: ${relatedTask.title}`) : ""
  );
  const [message, setMessage] = useState("");
  const [when, setWhen] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Pickers, only when the reminder isn't opened from a task.
  const projects = useAsync(
    () =>
      !relatedTask && manager
        ? listProjects({ mine: true, status: "active", page_size: 100 }).then((page) => page.items.filter((p) => p.permissions.can_review))
        : Promise.resolve([]),
    [relatedTask?.id, manager]
  );
  const tasks = useAsync(
    () =>
      relatedTask
        ? Promise.resolve([])
        : manager
          ? projectId
            ? listTasks({ scope: "managed", project_id: projectId, page_size: 100 }).then((page) => page.items)
            : Promise.resolve([])
          : listTasks({ scope: "assigned", page_size: 100 }).then((page) => page.items),
    [relatedTask?.id, manager, projectId]
  );
  const ready = Boolean(taskId || (manager && projectId));
  const people = useAsync(
    () =>
      ready
        ? reminderRecipients({ related_task_id: taskId || null, project_id: taskId ? null : projectId })
        : Promise.resolve([]),
    [taskId, projectId, ready]
  );

  const toggle = (id: string) =>
    setRecipients((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const reminder = await createTask({
        task_type: "reminder",
        title: title.trim(),
        description: message,
        project_id: taskId ? null : projectId || null,
        related_task_id: taskId || null,
        priority: "medium",
        due_at: localInputToIso(when),
        assignee_ids: recipients,
      });
      onSent(reminder);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const available = people.data ?? [];
  const chosen = recipients.filter((id) => available.some((p) => p.user.id === id));

  return (
    <Modal
      open={open}
      title={manager ? "Send a reminder" : "Remind your professor"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="reminder-form" loading={busy} disabled={!title.trim() || chosen.length === 0}>
            <BellRing className="h-4 w-4" aria-hidden="true" /> Send reminder
          </Button>
        </>
      }
    >
      <form id="reminder-form" className="space-y-4" onSubmit={(event) => void submit(event)}>
        {relatedTask ? (
          <p className="rounded-lg bg-surface-muted px-3 py-2 text-sm text-fg-soft">
            About <strong className="font-medium text-fg">{relatedTask.title}</strong>
            {relatedTask.project_title ? ` · ${relatedTask.project_title}` : ""}
          </p>
        ) : (
          <>
            {manager && (
              <Field label="Project">
                {(id) => (
                  <Select id={id} value={projectId} onChange={(e) => { setProjectId(e.target.value); setTaskId(""); setRecipients([]); }}>
                    <option value="">Choose a project…</option>
                    {(projects.data ?? []).map((p) => (
                      <option key={p.id} value={p.id}>{p.title}</option>
                    ))}
                  </Select>
                )}
              </Field>
            )}
            {(!manager || projectId) && (
              <Field label={manager ? "About a task (optional)" : "About which task"} hint={manager ? undefined : "Students can remind professors about tasks assigned to them."}>
                {(id) => (
                  <Select id={id} value={taskId} onChange={(e) => { setTaskId(e.target.value); setRecipients([]); }}>
                    <option value="">{manager ? "No particular task" : "Choose a task…"}</option>
                    {(tasks.data ?? [])
                      .filter((t) => t.task_type === "official")
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.title}{t.project_title ? ` · ${t.project_title}` : ""}
                        </option>
                      ))}
                  </Select>
                )}
              </Field>
            )}
          </>
        )}

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-fg-soft">{manager ? "Send to" : "Professor"}</legend>
          {!ready ? (
            <p className="text-sm text-fg-muted">{manager ? "Choose a project first." : "Choose a task first."}</p>
          ) : people.loading && !people.data ? (
            <Loading />
          ) : available.length === 0 ? (
            <p className="text-sm text-fg-muted">
              {manager ? "No other active members in this project." : "This project has no professor to remind."}
            </p>
          ) : (
            <ul className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-line p-2">
              {available.map((person) => (
                <li key={person.user.id}>
                  <label className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-surface-muted">
                    <input type="checkbox" checked={recipients.includes(person.user.id)} onChange={() => toggle(person.user.id)} />
                    <span className="min-w-0 flex-1 truncate">
                      {person.user.full_name} <span className="text-xs text-fg-muted">@{person.user.username}</span>
                    </span>
                    <span className="text-xs text-fg-muted">{humanize(person.membership_role)}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          {people.error && <p className="text-xs text-danger-fg">{people.error}</p>}
        </fieldset>

        <Field label="Reminder">
          {(id) => <Input id={id} maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Please review my submission" />}
        </Field>
        <Field label="Message (optional)">
          {(id) => <Textarea id={id} rows={3} value={message} onChange={(e) => setMessage(e.target.value)} />}
        </Field>
        <Field label="When (optional)" hint="Shown as the reminder's date; recipients also get a Discord nudge shortly before it.">
          {(id) => <Input id={id} type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />}
        </Field>
        <p className="text-xs text-fg-muted">Each recipient gets a private Discord message (if they linked Discord and keep task notifications on).</p>
        {error && <Alert>{error}</Alert>}
      </form>
    </Modal>
  );
}
