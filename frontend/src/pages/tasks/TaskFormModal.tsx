import { useState, type FormEvent } from "react";

import { Alert, Badge, Button, Field, Input, Modal, Select, Textarea } from "../../components/ui";
import { isoToLocalInput, localInputToIso } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import type { ProjectMember } from "../../services/projectService";
import { createTask, updateTask, type Task, type TaskPriority, type TaskType } from "../../services/taskService";

export default function TaskFormModal({
  open,
  taskType,
  projectId,
  members = [],
  task,
  onClose,
  onSaved,
}: {
  open: boolean;
  taskType: TaskType;
  projectId?: string | null;
  members?: ProjectMember[];
  task?: Task | null;
  onClose: () => void;
  onSaved: (task: Task) => void;
}) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [priority, setPriority] = useState<TaskPriority>(task?.priority ?? "medium");
  const [due, setDue] = useState(isoToLocalInput(task?.due_at));
  const [assignees, setAssignees] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Official tasks go to student members (owner or member role).
  const assignable = members.filter(
    (m) => m.membership_status === "active" && (m.membership_role === "member" || m.membership_role === "owner") && m.user.roles.includes("Student")
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const saved = task
        ? await updateTask(task.id, {
            title,
            description,
            priority,
            due_at: localInputToIso(due),
            clear_due_at: !due,
          })
        : await createTask({
            task_type: taskType,
            title,
            description,
            priority,
            due_at: localInputToIso(due),
            project_id: projectId ?? null,
            assignee_ids: taskType === "official" ? assignees : [],
          });
      onSaved(saved);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const heading = task ? "Edit task" : taskType === "official" ? "New official task" : "New personal task";

  return (
    <Modal
      open={open}
      title={heading}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="task-form" loading={saving}>Save</Button>
        </>
      }
    >
      <form id="task-form" onSubmit={submit} className="space-y-4">
        <Field label="Title">{(id) => <Input id={id} value={title} required maxLength={200} onChange={(e) => setTitle(e.target.value)} />}</Field>
        <Field label="Description">{(id) => <Textarea id={id} value={description} onChange={(e) => setDescription(e.target.value)} />}</Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Priority">
            {(id) => (
              <Select id={id} value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </Select>
            )}
          </Field>
          <Field label="Due date" hint="Shown in your local timezone.">
            {(id) => <Input id={id} type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />}
          </Field>
        </div>
        {!task && taskType === "official" && (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-700">Assign to students</legend>
            {assignable.length === 0 ? (
              <p className="text-xs text-slate-500">No student members yet. You can assign later.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {assignable.map((member) => {
                  const selected = assignees.includes(member.user.id);
                  return (
                    <button
                      key={member.user.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() =>
                        setAssignees(selected ? assignees.filter((id) => id !== member.user.id) : [...assignees, member.user.id])
                      }
                    >
                      <Badge tone={selected ? "blue" : "slate"}>{member.user.full_name}</Badge>
                    </button>
                  );
                })}
              </div>
            )}
            <p className="text-xs text-slate-500">Each student gets an independent status and submission history.</p>
          </fieldset>
        )}
        {taskType === "personal" && !task && <p className="text-xs text-slate-500">Personal tasks are private to you.</p>}
        {error && <Alert>{error}</Alert>}
      </form>
    </Modal>
  );
}
