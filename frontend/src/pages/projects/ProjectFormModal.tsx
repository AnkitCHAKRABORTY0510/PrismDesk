import { useState, type FormEvent } from "react";

import { Alert, Button, Field, Input, Modal, Textarea } from "../../components/ui";
import { getErrorMessage } from "../../services/api";
import { createProject, updateProject, type Project } from "../../services/projectService";

export default function ProjectFormModal({
  open,
  project,
  onClose,
  onSaved,
}: {
  open: boolean;
  project?: Project | null;
  onClose: () => void;
  onSaved: (project: Project) => void;
}) {
  const [title, setTitle] = useState(project?.title ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [objectives, setObjectives] = useState(project?.objectives ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (title.trim().length < 3) {
      setError("Title must contain at least 3 characters.");
      return;
    }
    setSaving(true);
    try {
      const input = { title: title.trim(), description, objectives };
      onSaved(project ? await updateProject(project.id, input) : await createProject(input));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={project ? "Edit project" : "Create project"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="project-form" loading={saving}>Save</Button>
        </>
      }
    >
      <form id="project-form" onSubmit={submit} className="space-y-4">
        <Field label="Project title">{(id) => <Input id={id} value={title} maxLength={200} required onChange={(e) => setTitle(e.target.value)} />}</Field>
        <Field label="Description">{(id) => <Textarea id={id} value={description} onChange={(e) => setDescription(e.target.value)} />}</Field>
        <Field label="Research objectives">{(id) => <Textarea id={id} value={objectives} onChange={(e) => setObjectives(e.target.value)} />}</Field>
        {!project && (
          <p className="text-xs text-fg-muted">
            You become the project owner. Administrators and supervising professors manage membership.
          </p>
        )}
        {error && <Alert>{error}</Alert>}
      </form>
    </Modal>
  );
}
