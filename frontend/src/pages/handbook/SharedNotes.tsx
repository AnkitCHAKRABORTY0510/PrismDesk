import { useEffect, useRef, useState } from "react";
import { History, PenLine, Users } from "lucide-react";

import { Alert, Button, Textarea, useToast } from "../../components/ui";
import { wordCount, type ISODate } from "../../lib/calendar";
import { formatDateTime } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import {
  addSharedComment,
  createSharedNote,
  sharedNoteVersions,
  updateSharedNote,
  type SharedComment,
  type SharedNote,
} from "../../services/handbookService";
import { RULED, readStorage, writeStorage } from "./plannerMeta";
import { VersionHistory } from "./VersionHistory";

const SHARED_FIELDS = [["body", "Shared note"]] as const;

function sharedDraftKey(userId: string, day: ISODate) {
  return `prismdesk.handbook.shared-draft.${userId}.${day}`;
}

interface Draft {
  body: string;
  saved_at: string;
}

function readDraft(key: string): Draft | null {
  const raw = readStorage(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Draft;
  } catch {
    return null;
  }
}

// --- Comment threads (supervisor feedback on a shared note) -----------------------

export function SharedCommentThreads({
  note,
  canReply,
  onChanged,
}: {
  note: SharedNote;
  canReply: boolean;
  onChanged: (note: SharedNote) => void;
}) {
  const { notify } = useToast();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const post = async (body: string, parentId?: string) => {
    setBusy(true);
    try {
      onChanged(await addSharedComment(note.id, body.trim(), parentId));
      return true;
    } catch (err) {
      notify(getErrorMessage(err), "error");
      return false;
    } finally {
      setBusy(false);
    }
  };

  if (!note.comments.length && !note.can_comment) return null;

  return (
    <div className="space-y-3">
      {note.comments.length > 0 && (
        <ul className="space-y-3" aria-label="Supervisor comments">
          {note.comments.map((comment) => (
            <Thread key={comment.id} comment={comment} canReply={canReply || note.can_comment} busy={busy} onReply={(body) => post(body, comment.id)} />
          ))}
        </ul>
      )}
      {note.can_comment && (
        <div className="space-y-2">
          <Textarea aria-label={`Comment on ${note.student.full_name}'s note`} rows={2} value={text} onChange={(e) => setText(e.target.value)} placeholder="Leave feedback…" />
          <Button size="sm" disabled={!text.trim() || busy} onClick={async () => (await post(text)) && setText("")}>
            Comment
          </Button>
        </div>
      )}
    </div>
  );
}

function Thread({ comment, canReply, busy, onReply }: { comment: SharedComment; canReply: boolean; busy: boolean; onReply: (body: string) => Promise<boolean> }) {
  const [open, setOpen] = useState(false);
  const [reply, setReply] = useState("");
  return (
    <li className="rounded-lg bg-surface-muted p-3 text-sm">
      <div className="text-xs text-fg-muted">{comment.author?.full_name ?? "Former user"} · {formatDateTime(comment.created_at)}</div>
      <p className="mt-1 whitespace-pre-line text-fg-soft">{comment.body}</p>
      {comment.replies.length > 0 && (
        <ul className="mt-2 space-y-2 border-l-2 border-line pl-3">
          {comment.replies.map((r) => (
            <li key={r.id}>
              <div className="text-xs text-fg-muted">{r.author?.full_name ?? "Former user"} · {formatDateTime(r.created_at)}</div>
              <p className="whitespace-pre-line text-fg-soft">{r.body}</p>
            </li>
          ))}
        </ul>
      )}
      {canReply &&
        (open ? (
          <div className="mt-2 space-y-2">
            <Textarea aria-label="Reply" rows={2} value={reply} onChange={(e) => setReply(e.target.value)} />
            <Button size="sm" disabled={!reply.trim() || busy} onClick={async () => { if (await onReply(reply)) { setReply(""); setOpen(false); } }}>
              Reply
            </Button>
          </div>
        ) : (
          <button type="button" className="mt-2 text-xs font-medium text-link" onClick={() => setOpen(true)}>Reply</button>
        ))}
    </li>
  );
}

// --- The student's own shared note ---------------------------------------------------

export function SharedNoteEditor({
  day,
  userId,
  note,
  onSaved,
  onDirtyChange,
  onOpenChild,
}: {
  day: ISODate;
  userId: string;
  note: SharedNote | null;
  onSaved: (note: SharedNote) => void;
  onDirtyChange: (dirty: boolean) => void;
  onOpenChild: (open: boolean) => void;
}) {
  const key = sharedDraftKey(userId, day);
  const saved = note?.body ?? "";
  const [editing, setEditing] = useState(() => readDraft(key) !== null);
  const [body, setBody] = useState(() => readDraft(key)?.body ?? saved);
  const [restoredAt, setRestoredAt] = useState(() => readDraft(key)?.saved_at ?? "");
  const [draftSavedAt, setDraftSavedAt] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const dirty = editing && body !== saved;
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  useEffect(() => {
    if (!dirty) return;
    const timer = window.setTimeout(() => {
      const at = new Date().toISOString();
      writeStorage(key, JSON.stringify({ body, saved_at: at }));
      setDraftSavedAt(at);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [dirty, body, key]);

  useEffect(() => {
    if (!dirty) return;
    const handler = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const start = () => {
    setBody(saved);
    setEditing(true);
    window.setTimeout(() => textRef.current?.focus(), 0);
  };

  const discard = () => {
    writeStorage(key, null);
    setRestoredAt("");
    setDraftSavedAt("");
    setBody(saved);
    setEditing(false);
  };

  const save = async () => {
    if (!body.trim()) {
      setError("Write something before sharing it.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = note ? await updateSharedNote(note.id, body) : await createSharedNote(day, body);
      writeStorage(key, null);
      setRestoredAt("");
      setDraftSavedAt("");
      setEditing(false);
      onSaved(result);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const openHistory = (open: boolean) => {
    setHistory(open);
    onOpenChild(open);
  };
  const words = wordCount(editing ? body : saved);

  return (
    <div className="space-y-3">
      {restoredAt && editing && (
        <Alert kind="info">
          <span className="flex flex-wrap items-center justify-between gap-2">
            <span>Restored your unsaved shared draft from {formatDateTime(restoredAt)}.</span>
            <button type="button" onClick={discard} className="text-xs font-medium underline underline-offset-2">Discard draft</button>
          </span>
        </Alert>
      )}
      {editing ? (
        <div className="rounded-xl border border-info-line bg-info-soft/60 p-3 sm:p-4">
          <label className="block">
            <span className="sr-only">Note shared with your supervisors</span>
            <textarea
              ref={textRef}
              aria-label="Note shared with your supervisors"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={4}
              placeholder="What should your supervisor know about today? Progress, blockers, questions…"
              className="block w-full resize-y bg-transparent font-serif text-[1.05rem] text-fg outline-none placeholder:italic placeholder:text-fg-subtle"
              style={RULED}
            />
          </label>
        </div>
      ) : note ? (
        <div className="rounded-xl border border-info-line bg-info-soft/60 p-3 sm:p-4">
          <p className="whitespace-pre-line font-serif text-[1.05rem] text-fg" style={RULED}>{note.body}</p>
        </div>
      ) : (
        <button
          type="button"
          onClick={start}
          className="flex w-full items-center gap-3 rounded-xl border border-dashed border-info-line px-4 py-4 text-left text-sm text-fg-muted transition-colors hover:bg-info-soft/60"
        >
          <PenLine className="h-4 w-4 shrink-0 text-info-fg" aria-hidden="true" />
          Write a note for your supervisor about today…
        </button>
      )}
      {error && <Alert>{error}</Alert>}
      {(editing || note) && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-muted">
            <span>{words} {words === 1 ? "word" : "words"}</span>
            {note && <span>Shared {formatDateTime(note.updated_at)} · version {note.version}</span>}
            {dirty && <span className="text-warn-fg">Unsaved changes{draftSavedAt ? " · draft kept on this device" : ""}</span>}
          </div>
          <div className="flex gap-2">
            {!editing && note && note.version > 1 && (
              <Button size="sm" variant="ghost" onClick={() => openHistory(true)}>
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                History
              </Button>
            )}
            {editing ? (
              <>
                <Button size="sm" variant="secondary" onClick={discard} disabled={saving}>Cancel</Button>
                <Button size="sm" onClick={save} loading={saving} disabled={!dirty}>{note ? "Save shared note" : "Share with supervisor"}</Button>
              </>
            ) : (
              <Button size="sm" variant="secondary" onClick={start} aria-label="Edit shared note">
                <PenLine className="h-3.5 w-3.5" aria-hidden="true" />
                Edit
              </Button>
            )}
          </div>
        </div>
      )}
      {note && <SharedCommentThreads note={note} canReply onChanged={onSaved} />}
      {history && note && (
        <VersionHistory title="Shared note history" load={() => sharedNoteVersions(note.id)} fields={SHARED_FIELDS} onClose={() => openHistory(false)} />
      )}
    </div>
  );
}

// --- What a supervisor sees for one day -------------------------------------------

export function SupervisorSharedNotes({
  notes,
  onChanged,
}: {
  notes: SharedNote[];
  onChanged: (note: SharedNote) => void;
}) {
  return (
    <section aria-labelledby="shared-notes-heading" className="space-y-3">
      <h3 id="shared-notes-heading" className="flex items-center gap-2 text-sm font-semibold text-fg">
        <Users className="h-4 w-4 text-info-fg" aria-hidden="true" />
        Notes shared by your students
      </h3>
      {notes.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line-strong px-4 py-4 text-center text-sm text-fg-muted">
          No student shared a note for this day.
        </p>
      ) : (
        <ul className="space-y-4">
          {notes.map((note) => (
            <li key={note.id} className="space-y-3 rounded-xl border border-info-line bg-surface p-4 shadow-card">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-medium text-fg">{note.student.full_name}</p>
                <span className="text-xs text-fg-muted">v{note.version} · {formatDateTime(note.updated_at)}</span>
              </div>
              <p className="whitespace-pre-line font-serif text-[1.05rem] text-fg-soft">{note.body}</p>
              <SharedCommentThreads note={note} canReply={note.can_comment} onChanged={onChanged} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
