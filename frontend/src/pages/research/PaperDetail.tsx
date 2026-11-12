import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  ErrorMessage,
  ExternalLink,
  Loading,
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
  deletePaper,
  getPaper,
  listNotes,
  updateNote,
  type Note,
} from "../../services/researchService";
import { ReadingStatusToggle } from "../../components/research/ReadingStatusToggle";
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
  const [removingPaper, setRemovingPaper] = useState(false);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  // The list passes its URL (with search and filters) so going back keeps them.
  const backState = location.state as { backTo?: unknown } | null;
  const backTo =
    typeof backState?.backTo === "string" && backState.backTo.startsWith("/research") ? backState.backTo : "/research";
  const canBrowseLibrary = can(user, "research.view");

  const backLink = canBrowseLibrary && (
    <Link to={backTo} className="inline-flex items-center gap-1 text-sm text-fg-muted hover:text-link">
      <span aria-hidden="true">←</span> Back to library
    </Link>
  );

  if (paper.loading && !paper.data) return <Loading />;
  if (paper.error)
    return (
      <div className="space-y-4">
        {backLink}
        <ErrorMessage message={paper.error} onRetry={paper.reload} />
      </div>
    );
  if (!paper.data) return null;
  const p = paper.data;

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
      {backLink}
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
                className="inline-flex h-10 items-center rounded-lg bg-[#5865F2] px-4 text-sm font-medium text-white hover:bg-[#4752c4]"
              >
                Discuss on Discord
              </a>
            )}
            {p.can_edit && <Button variant="secondary" onClick={() => setEditing(true)}>Edit metadata</Button>}
            {p.can_edit && <Button variant="danger" onClick={() => setRemovingPaper(true)}>Delete paper</Button>}
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Details" className="lg:col-span-2">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-fg-muted">Year</dt><dd>{p.publication_year ?? "—"}</dd></div>
            <div><dt className="text-fg-muted">Journal / conference</dt><dd>{p.venue ?? "—"}</dd></div>
            <div><dt className="text-fg-muted">DOI</dt><dd>{p.doi ? <ExternalLink href={`https://doi.org/${p.doi}`}>{p.doi}</ExternalLink> : "—"}</dd></div>
            <div><dt className="text-fg-muted">External URL</dt><dd>{p.url ? <ExternalLink href={p.url} /> : "—"}</dd></div>
            <div className="sm:col-span-2">
              <dt className="text-fg-muted">Keywords</dt>
              <dd className="mt-1 flex flex-wrap gap-1">{p.keywords.length ? p.keywords.map((k) => <Badge key={k}>{k}</Badge>) : "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-fg-muted">Projects</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {p.projects.length
                  ? p.projects.map((project) => (
                      <Link key={project.id} to={`/projects/${project.id}`} className="text-link hover:underline">
                        {project.title}
                      </Link>
                    ))
                  : "Not linked to any of your projects"}
              </dd>
            </div>
          </dl>
          {p.abstract && <p className="mt-4 whitespace-pre-line text-sm text-fg-soft">{p.abstract}</p>}
        </Card>

        <div className="space-y-6">
          {can(user, "research.track_progress") && (
            <Card title="My reading status">
              <ReadingStatusToggle
                paperId={p.id}
                paperTitle={p.title}
                status={p.my_status}
                onChange={(next) => paper.setData({ ...p, my_status: next })}
              />
            </Card>
          )}

          <Card title="My private notes">
            <p className="mb-3 text-xs text-fg-muted">Only you can see these notes — not professors or administrators.</p>
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
                <li key={note.id} className="rounded-lg bg-surface-muted p-3 text-sm">
                  <p className="whitespace-pre-line">{note.content}</p>
                  <div className="mt-2 flex items-center justify-between text-xs text-fg-muted">
                    <span>{formatDateTime(note.updated_at)}</span>
                    <span className="flex gap-2">
                      <button type="button" className="hover:text-link" onClick={() => { setEditingNote(note); setDraft(note.content); }}>Edit</button>
                      <button type="button" className="hover:text-danger-fg" onClick={() => setDeleting(note)}>Delete</button>
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
        open={removingPaper}
        title="Delete paper"
        message={`Delete “${p.title}”? This can't be undone. Its project links, reading progress and notes are removed too.`}
        confirmLabel="Delete"
        danger
        busy={busy}
        onCancel={() => setRemovingPaper(false)}
        onConfirm={async () => {
          setBusy(true);
          try {
            await deletePaper(p.id);
            notify("Paper deleted.");
            navigate(canBrowseLibrary ? backTo : "/dashboard", { replace: true });
          } catch (err) {
            notify(getErrorMessage(err), "error");
            setBusy(false);
            setRemovingPaper(false);
          }
        }}
      />
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
