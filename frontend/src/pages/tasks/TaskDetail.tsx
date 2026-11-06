import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Alert,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  ErrorMessage,
  ExternalLink,
  Field,
  Loading,
  Select,
  StatusBadge,
  Textarea,
  useToast,
} from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime, humanize, splitList } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { listMembers } from "../../services/projectService";
import {
  addAssignees,
  changeStatus,
  deleteTask,
  getTask,
  listSubmissions,
  reviewSubmission,
  submitWork,
  type Assignment,
  type AssignmentStatus,
  type Task,
} from "../../services/taskService";
import TaskFormModal from "./TaskFormModal";

// Status moves an assignee can make directly (others happen through
// submission and review). Mirrors the backend rules for convenience.
const NEXT: Record<"official" | "personal", Partial<Record<AssignmentStatus, AssignmentStatus[]>>> = {
  official: { todo: ["in_progress"], in_progress: ["todo"], revision_required: ["in_progress"] },
  personal: { todo: ["in_progress", "completed"], in_progress: ["todo", "completed"], completed: ["in_progress"] },
};

export default function TaskDetail() {
  const { taskId = "" } = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const task = useAsync(() => getTask(taskId), [taskId]);
  const [selected, setSelected] = useState<string | null>(search.get("assignment"));
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (task.loading && !task.data) return <Loading />;
  if (task.error) return <ErrorMessage message={task.error} onRetry={task.reload} />;
  if (!task.data) return null;
  const t = task.data;
  const assignment = t.assignments.find((a) => a.id === selected) ?? t.my_assignment ?? t.assignments[0] ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t.title}
        description={
          <span>
            {t.task_type === "personal" ? "Personal task" : <>Official task · <Link className="text-brand" to={`/projects/${t.project_id}`}>{t.project_title}</Link></>}
            {" · "}Due {formatDateTime(t.due_at)} · Priority {humanize(t.priority)}
          </span>
        }
        actions={
          t.can_manage && (
            <>
              <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
              <Button variant="danger" onClick={() => setConfirmDelete(true)}>Delete</Button>
            </>
          )
        }
      />
      {t.is_overdue && <Alert>This task is past its due date.</Alert>}
      {t.description && (
        <Card title="Description">
          <p className="whitespace-pre-line text-sm text-slate-700">{t.description}</p>
        </Card>
      )}

      {t.can_manage && t.task_type === "official" && (
        <AssigneesCard task={t} selected={assignment?.id ?? null} onSelect={setSelected} onChanged={task.reload} />
      )}

      {assignment && (
        <AssignmentPanel
          key={assignment.id}
          task={t}
          assignment={assignment}
          isMine={assignment.id === t.my_assignment?.id}
          onChanged={task.reload}
        />
      )}

      {editing && (
        <TaskFormModal
          open
          task={t}
          taskType={t.task_type}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            setEditing(false);
            task.setData(saved);
            notify("Task updated.");
          }}
        />
      )}
      <ConfirmDialog
        open={confirmDelete}
        title="Delete task"
        message="Delete this task together with its assignments and submission history?"
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          try {
            await deleteTask(t.id);
            notify("Task deleted.");
            navigate("/tasks");
          } catch (err) {
            notify(getErrorMessage(err), "error");
          }
        }}
      />
    </div>
  );
}

function AssigneesCard({
  task,
  selected,
  onSelect,
  onChanged,
}: {
  task: Task;
  selected: string | null;
  onSelect: (id: string) => void;
  onChanged: () => Promise<void>;
}) {
  const { notify } = useToast();
  const members = useAsync(() => (task.project_id ? listMembers(task.project_id) : Promise.resolve([])), [task.project_id]);
  const [adding, setAdding] = useState("");
  const assignedIds = task.assignments.map((a) => a.assignee.id);
  const candidates = (members.data ?? []).filter(
    (m) => ["member", "owner"].includes(m.membership_role) && m.user.roles.includes("Student") && !assignedIds.includes(m.user.id)
  );

  return (
    <Card
      title="Assigned students"
      actions={
        candidates.length > 0 && (
          <div className="flex gap-2">
            <Select aria-label="Student to assign" value={adding} onChange={(e) => setAdding(e.target.value)}>
              <option value="">Add student…</option>
              {candidates.map((m) => (
                <option key={m.user.id} value={m.user.id}>{m.user.full_name}</option>
              ))}
            </Select>
            <Button
              size="sm"
              disabled={!adding}
              onClick={async () => {
                try {
                  await addAssignees(task.id, [adding]);
                  setAdding("");
                  await onChanged();
                } catch (err) {
                  notify(getErrorMessage(err), "error");
                }
              }}
            >
              Assign
            </Button>
          </div>
        )
      }
    >
      <DataTable<Assignment>
        rows={task.assignments}
        rowKey={(row) => row.id}
        empty="No students assigned yet."
        onRowClick={(row) => onSelect(row.id)}
        columns={[
          { header: "Student", cell: (row) => <span className={row.id === selected ? "font-semibold text-brand" : ""}>{row.assignee.full_name}</span> },
          { header: "Status", cell: (row) => <StatusBadge status={row.status} /> },
          { header: "Submissions", cell: (row) => row.submission_count },
          { header: "Updated", cell: (row) => formatDateTime(row.updated_at) },
        ]}
      />
    </Card>
  );
}

function AssignmentPanel({
  task,
  assignment,
  isMine,
  onChanged,
}: {
  task: Task;
  assignment: Assignment;
  isMine: boolean;
  onChanged: () => Promise<void>;
}) {
  const { notify } = useToast();
  const submissions = useAsync(
    () => (task.task_type === "official" ? listSubmissions(assignment.id) : Promise.resolve([])),
    [assignment.id, assignment.status]
  );
  const [text, setText] = useState("");
  const [links, setLinks] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    try {
      await action();
      notify(message);
      await onChanged();
      await submissions.reload();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const nextStatuses = isMine ? NEXT[task.task_type][assignment.status] ?? [] : [];
  const canSubmit = isMine && task.task_type === "official" && ["todo", "in_progress", "revision_required"].includes(assignment.status);
  const latest = submissions.data?.[0];
  const canReview = !isMine && task.can_manage && assignment.status === "under_review" && latest;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title={isMine ? "My progress" : `${assignment.assignee.full_name}'s progress`}>
        <div className="flex items-center gap-3 text-sm">
          Current status: <StatusBadge status={assignment.status} />
        </div>
        {nextStatuses.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {nextStatuses.map((status) => (
              <Button key={status} size="sm" variant="secondary" disabled={busy} onClick={() => void run(() => changeStatus(assignment.id, status), `Moved to ${humanize(status)}.`)}>
                Move to {humanize(status)}
              </Button>
            ))}
          </div>
        )}

        {canSubmit && (
          <form
            className="mt-6 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void run(() => submitWork(assignment.id, text, splitList(links)), "Submission sent for review.").then(() => {
                setText("");
                setLinks("");
              });
            }}
          >
            <Field label="Response">{(id) => <Textarea id={id} rows={5} value={text} onChange={(e) => setText(e.target.value)} />}</Field>
            <Field label="External links" hint="One per line or comma-separated (GitHub, Overleaf, Drive…). File uploads are not supported.">
              {(id) => <Textarea id={id} rows={2} value={links} onChange={(e) => setLinks(e.target.value)} />}
            </Field>
            <Button type="submit" loading={busy} disabled={!text.trim() && !links.trim()}>
              {assignment.status === "revision_required" ? "Resubmit" : "Submit for review"}
            </Button>
          </form>
        )}

        {canReview && latest && (
          <div className="mt-6 space-y-3">
            <Field label={`Review version ${latest.version}`}>
              {(id) => <Textarea id={id} rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Feedback for the student" />}
            </Field>
            <div className="flex gap-2">
              <Button variant="success" loading={busy} onClick={() => void run(() => reviewSubmission(latest.id, "approved", feedback), "Submission approved.")}>
                Approve & complete
              </Button>
              <Button
                variant="secondary"
                disabled={busy || !feedback.trim()}
                onClick={() => void run(() => reviewSubmission(latest.id, "revision_required", feedback), "Revision requested.")}
              >
                Request revision
              </Button>
            </div>
          </div>
        )}
        {error && <div className="mt-4"><Alert>{error}</Alert></div>}
      </Card>

      {task.task_type === "official" && (
        <Card title="Submission history">
          <ErrorMessage message={submissions.error} />
          {submissions.loading && !submissions.data ? (
            <Loading />
          ) : (submissions.data ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">No submissions yet.</p>
          ) : (
            <ol className="space-y-4">
              {(submissions.data ?? []).map((s) => (
                <li key={s.id} className="rounded-lg border border-slate-200 p-3 text-sm">
                  <div className="flex justify-between text-xs text-slate-500">
                    <strong className="text-slate-700">Version {s.version}</strong>
                    <span>{formatDateTime(s.submitted_at)}</span>
                  </div>
                  {s.response_text && <p className="mt-2 whitespace-pre-line">{s.response_text}</p>}
                  {s.links.length > 0 && (
                    <ul className="mt-2 list-disc pl-5">
                      {s.links.map((link) => <li key={link}><ExternalLink href={link} /></li>)}
                    </ul>
                  )}
                  {s.reviews.map((r) => (
                    <div key={r.id} className="mt-3 rounded-md bg-slate-50 p-2">
                      <div className="flex items-center gap-2 text-xs">
                        <StatusBadge status={r.decision === "approved" ? "completed" : "revision_required"} />
                        <span className="text-slate-500">{r.reviewer?.full_name} · {formatDateTime(r.created_at)}</span>
                      </div>
                      {r.feedback && <p className="mt-1 whitespace-pre-line">{r.feedback}</p>}
                    </div>
                  ))}
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
    </div>
  );
}
