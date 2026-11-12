import { useState } from "react";
import { Link, useParams } from "react-router";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import { Button, Card, ErrorMessage, ExternalLink, Loading, Textarea, useToast } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { addDays } from "../../lib/calendar";
import { formatDate, formatDateTime } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { addComment, entryVersions, getEntry, listEntries, type HandbookComment, type HandbookEntry } from "../../services/handbookService";
import EntryFormModal from "./EntryFormModal";
import { ENTRY_FIELDS } from "./plannerMeta";
import { VersionHistory } from "./VersionHistory";

const SECTIONS = [
  ["work_completed", "Work completed"],
  ["research_progress", "Research progress"],
  ["problems", "Problems encountered"],
  ["next_steps", "Next steps"],
] as const;

export default function EntryDetail() {
  const { entryId = "" } = useParams();
  const { notify } = useToast();
  const entry = useAsync(() => getEntry(entryId), [entryId]);
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [comment, setComment] = useState("");
  const neighbours = useAsync(async () => (entry.data ? findNeighbours(entry.data) : null), [entry.data?.id]);

  if (entry.loading && !entry.data) return <Loading />;
  if (entry.error) return <ErrorMessage message={entry.error} onRetry={entry.reload} />;
  if (!entry.data) return null;
  const e = entry.data;

  const post = async (body: string, parentId?: string) => {
    try {
      entry.setData(await addComment(e.id, body, parentId));
      return true;
    } catch (err) {
      notify(getErrorMessage(err), "error");
      return false;
    }
  };

  const isStudentView = e.can_edit;
  const canStartThread = e.can_comment && !isStudentView;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${formatDate(e.entry_date)} · ${e.project_title ?? "Project"}`}
        description={<>By {e.student.full_name} · version {e.version} · <Link className="text-link" to={`/projects/${e.project_id}`}>Open project</Link></>}
        actions={
          <>
            <Link
              to={`/handbook?open=${e.entry_date}`}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 text-sm font-medium text-fg-soft shadow-sm hover:bg-surface-muted hover:text-fg"
            >
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              Day page
            </Link>
            <Button variant="secondary" onClick={() => setShowHistory(true)}>Edit history{e.version > 1 ? ` (${e.version})` : ""}</Button>
            {e.can_edit && <Button onClick={() => setEditing(true)}>Edit entry</Button>}
          </>
        }
      />
      <nav aria-label="Other days of this project" className="flex items-center justify-between gap-2 text-sm">
        {neighbours.data?.prev ? (
          <Link to={`/handbook/entries/${neighbours.data.prev.id}`} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-link hover:bg-surface-muted">
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            {formatDate(neighbours.data.prev.entry_date)}
          </Link>
        ) : (
          <span className="px-2 py-1 text-fg-subtle">No earlier entry</span>
        )}
        {neighbours.data?.next ? (
          <Link to={`/handbook/entries/${neighbours.data.next.id}`} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-link hover:bg-surface-muted">
            {formatDate(neighbours.data.next.entry_date)}
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        ) : (
          <span className="px-2 py-1 text-fg-subtle">No later entry</span>
        )}
      </nav>
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Entry">
          <div className="space-y-4 text-sm">
            {SECTIONS.map(([key, label]) => (
              <div key={key}>
                <h3 className="font-medium text-fg-soft">{label}</h3>
                {e[key] ? (
                  <p className="mt-1 whitespace-pre-line text-fg-soft">{e[key]}</p>
                ) : (
                  <p className="mt-1 text-sm italic text-fg-subtle">Nothing noted.</p>
                )}
              </div>
            ))}
            {e.references.length > 0 && (
              <div>
                <h3 className="font-medium text-fg-soft">References</h3>
                <ul className="mt-1 list-disc pl-5">{e.references.map((r) => <li key={r}><ExternalLink href={r} /></li>)}</ul>
              </div>
            )}
          </div>
        </Card>

        <Card title="Supervisor comments">
          {e.comments.length === 0 && <p className="text-sm text-fg-muted">No comments yet.</p>}
          <ul className="space-y-4">
            {e.comments.map((c) => (
              <CommentThread key={c.id} comment={c} canReply={e.can_comment} onReply={(body) => post(body, c.id)} />
            ))}
          </ul>
          {canStartThread && (
            <div className="mt-4 space-y-2">
              <Textarea aria-label="New comment" rows={3} value={comment} onChange={(ev) => setComment(ev.target.value)} placeholder="Add feedback for the student…" />
              <Button size="sm" disabled={!comment.trim()} onClick={async () => (await post(comment)) && setComment("")}>
                Comment
              </Button>
            </div>
          )}
        </Card>
      </div>

      {editing && (
        <EntryFormModal
          open
          entry={e}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            notify("Entry updated.");
            void entry.reload();
          }}
        />
      )}
      {showHistory && <VersionHistory load={() => entryVersions(e.id)} fields={ENTRY_FIELDS} onClose={() => setShowHistory(false)} />}
    </div>
  );
}

function CommentThread({
  comment,
  canReply,
  onReply,
}: {
  comment: HandbookComment;
  canReply: boolean;
  onReply: (body: string) => Promise<boolean>;
}) {
  const [reply, setReply] = useState("");
  const [open, setOpen] = useState(false);
  return (
    <li className="rounded-lg bg-surface-muted p-3 text-sm">
      <div className="text-xs text-fg-muted">{comment.author?.full_name ?? "Former user"} · {formatDateTime(comment.created_at)}</div>
      <p className="mt-1 whitespace-pre-line">{comment.body}</p>
      {comment.replies.length > 0 && (
        <ul className="mt-2 space-y-2 border-l-2 border-line pl-3">
          {comment.replies.map((r) => (
            <li key={r.id}>
              <div className="text-xs text-fg-muted">{r.author?.full_name ?? "Former user"} · {formatDateTime(r.created_at)}</div>
              <p className="whitespace-pre-line">{r.body}</p>
            </li>
          ))}
        </ul>
      )}
      {canReply &&
        (open ? (
          <div className="mt-2 space-y-2">
            <Textarea aria-label="Reply" rows={2} value={reply} onChange={(e) => setReply(e.target.value)} />
            <Button size="sm" disabled={!reply.trim()} onClick={async () => { if (await onReply(reply)) { setReply(""); setOpen(false); } }}>
              Reply
            </Button>
          </div>
        ) : (
          <button type="button" className="mt-2 text-xs text-link" onClick={() => setOpen(true)}>Reply</button>
        ))}
    </li>
  );
}

// The same student's previous and next entry on this project.
async function findNeighbours(entry: HandbookEntry) {
  const scope = { project_id: entry.project_id, student_id: entry.student.id };
  const [before, after] = await Promise.all([
    listEntries({ ...scope, date_to: addDays(entry.entry_date, -1), page_size: 1 }),
    listEntries({ ...scope, date_from: addDays(entry.entry_date, 1), page_size: 1 }),
  ]);
  // Entries come newest first, so the nearest later entry is the last one.
  const next = after.total > 1 ? (await listEntries({ ...scope, date_from: addDays(entry.entry_date, 1), page_size: 1, page: after.total })).items[0] : after.items[0];
  return { prev: before.items[0] ?? null, next: next ?? null };
}
