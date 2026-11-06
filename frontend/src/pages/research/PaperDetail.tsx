import { useState } from "react";
import { Link, useParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  ErrorMessage,
  ExternalLink,
  Loading,
  Select,
  Textarea,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import {
  createNote,
  deleteNote,
  getPaper,
  listNotes,
  setReadingStatus,
  updateNote,
  type Note,
  type ReadingStatus,
} from "../../services/researchService";
import PaperFormModal from "./PaperFormModal";

export default function PaperDetail() {
  const { paperId = "" } = useParams();
  const { user } = useAuth();
  const { notify } = useToast();
  const paper = useAsync(() => getPaper(paperId), [paperId]);
  const notes = useAsync(() => listNotes(paperId), [paperId]);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [deleting, setDeleting] = useState<Note | null>(null);

  if (paper.loading && !paper.data) return <Loading />;
  if (paper.error) return <ErrorMessage message={paper.error} onRetry={paper.reload} />;
  if (!paper.data) return null;
  const p = paper.data;

  const changeStatus = async (status: ReadingStatus) => {
    try {
      await setReadingStatus(p.id, status);
      paper.setData({ ...p, my_status: status });
      notify("Reading status updated.");
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  const saveNote = async () => {
    if (!draft.trim()) return;
    try {
      if (editingNote) await updateNote(editingNote.id, draft);
      else await createNote(p.id, draft);
      setDraft("");
      setEditingNote(null);
      await notes.reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={p.title}
        description={p.authors.join(", ")}
        actions={
          <>
            {p.discord_thread_url && (
              <a
                href={p.discord_thread_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center rounded-lg bg-[#5865F2] px-4 py-2 text-sm font-medium text-white hover:bg-[#4752c4]"
              >
                Discuss on Discord
              </a>
            )}
            {p.can_edit && <Button variant="secondary" onClick={() => setEditing(true)}>Edit metadata</Button>}
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Details" className="lg:col-span-2">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-slate-500">Year</dt><dd>{p.publication_year ?? "—"}</dd></div>
            <div><dt className="text-slate-500">Journal / conference</dt><dd>{p.venue ?? "—"}</dd></div>
            <div><dt className="text-slate-500">DOI</dt><dd>{p.doi ? <ExternalLink href={`https://doi.org/${p.doi}`}>{p.doi}</ExternalLink> : "—"}</dd></div>
            <div><dt className="text-slate-500">External URL</dt><dd>{p.url ? <ExternalLink href={p.url} /> : "—"}</dd></div>
            <div className="sm:col-span-2">
              <dt className="text-slate-500">Keywords</dt>
              <dd className="mt-1 flex flex-wrap gap-1">{p.keywords.length ? p.keywords.map((k) => <Badge key={k}>{k}</Badge>) : "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-slate-500">Projects</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {p.projects.length
                  ? p.projects.map((project) => (
                      <Link key={project.id} to={`/projects/${project.id}`} className="text-brand hover:underline">
                        {project.title}
                      </Link>
                    ))
                  : "Not linked to any of your projects"}
              </dd>
            </div>
          </dl>
          {p.abstract && <p className="mt-4 whitespace-pre-line text-sm text-slate-700">{p.abstract}</p>}
        </Card>

        <div className="space-y-6">
          {can(user, "research.track_progress") && (
            <Card title="My reading status">
              <Select aria-label="Reading status" value={p.my_status ?? "not_started"} onChange={(e) => void changeStatus(e.target.value as ReadingStatus)}>
                <option value="not_started">Not started</option>
                <option value="reading">Reading</option>
                <option value="completed">Completed</option>
              </Select>
            </Card>
          )}

          <Card title="My private notes">
            <p className="mb-3 text-xs text-slate-500">Only you can see these notes — not professors or administrators.</p>
            <Textarea aria-label="Note" rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Write a note…" />
            <div className="mt-2 flex gap-2">
              <Button size="sm" onClick={() => void saveNote()} disabled={!draft.trim()}>
                {editingNote ? "Update note" : "Add note"}
              </Button>
              {editingNote && (
                <Button size="sm" variant="ghost" onClick={() => { setEditingNote(null); setDraft(""); }}>
                  Cancel
                </Button>
              )}
            </div>
            <ErrorMessage message={notes.error} />
            <ul className="mt-4 space-y-3">
              {(notes.data ?? []).map((note) => (
                <li key={note.id} className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="whitespace-pre-line">{note.content}</p>
                  <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                    <span>{formatDateTime(note.updated_at)}</span>
                    <span className="flex gap-2">
                      <button type="button" className="hover:text-brand" onClick={() => { setEditingNote(note); setDraft(note.content); }}>Edit</button>
                      <button type="button" className="hover:text-red-600" onClick={() => setDeleting(note)}>Delete</button>
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      {editing && (
        <PaperFormModal
          open
          paper={p}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            setEditing(false);
            paper.setData(saved);
            notify("Paper updated.");
          }}
        />
      )}
      <ConfirmDialog
        open={deleting !== null}
        title="Delete note"
        message="Delete this private note permanently?"
        confirmLabel="Delete"
        danger
        onCancel={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          try {
            await deleteNote(deleting.id);
            setDeleting(null);
            await notes.reload();
          } catch (err) {
            notify(getErrorMessage(err), "error");
          }
        }}
      />
    </div>
  );
}
