import { useState } from "react";
import { Link, useParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import { Button, Card, ErrorMessage, ExternalLink, Loading, Modal, Textarea, useToast } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDate, formatDateTime, humanize } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { addComment, entryVersions, getEntry, type HandbookComment } from "../../services/handbookService";
import EntryFormModal from "./EntryFormModal";

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
        description={<>By {e.student.full_name} · version {e.version} · <Link className="text-brand" to={`/projects/${e.project_id}`}>Open project</Link></>}
        actions={
          <>
            <Button variant="secondary" onClick={() => setShowHistory(true)}>Edit history</Button>
            {e.can_edit && <Button onClick={() => setEditing(true)}>Edit entry</Button>}
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Entry">
          <div className="space-y-4 text-sm">
            {SECTIONS.map(([key, label]) => (
              <div key={key}>
                <h3 className="font-medium text-slate-700">{label}</h3>
                <p className="mt-1 whitespace-pre-line text-slate-600">{e[key] || "—"}</p>
              </div>
            ))}
            {e.references.length > 0 && (
              <div>
                <h3 className="font-medium text-slate-700">References</h3>
                <ul className="mt-1 list-disc pl-5">{e.references.map((r) => <li key={r}><ExternalLink href={r} /></li>)}</ul>
              </div>
            )}
          </div>
        </Card>

        <Card title="Supervisor comments">
          {e.comments.length === 0 && <p className="text-sm text-slate-500">No comments yet.</p>}
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
      {showHistory && <HistoryModal entryId={e.id} onClose={() => setShowHistory(false)} />}
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
    <li className="rounded-lg bg-slate-50 p-3 text-sm">
      <div className="text-xs text-slate-500">{comment.author?.full_name ?? "Former user"} · {formatDateTime(comment.created_at)}</div>
      <p className="mt-1 whitespace-pre-line">{comment.body}</p>
      {comment.replies.length > 0 && (
        <ul className="mt-2 space-y-2 border-l-2 border-slate-200 pl-3">
          {comment.replies.map((r) => (
            <li key={r.id}>
              <div className="text-xs text-slate-500">{r.author?.full_name ?? "Former user"} · {formatDateTime(r.created_at)}</div>
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
          <button type="button" className="mt-2 text-xs text-brand" onClick={() => setOpen(true)}>Reply</button>
        ))}
    </li>
  );
}

function HistoryModal({ entryId, onClose }: { entryId: string; onClose: () => void }) {
  const versions = useAsync(() => entryVersions(entryId), [entryId]);
  return (
    <Modal open wide title="Edit history" onClose={onClose}>
      <ErrorMessage message={versions.error} />
      {versions.loading && !versions.data ? (
        <Loading />
      ) : (
        <ol className="space-y-4">
          {(versions.data ?? []).map((v) => (
            <li key={v.version} className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="mb-2 text-xs text-slate-500">Version {v.version} · {formatDateTime(v.edited_at)}</div>
              {Object.entries(v.snapshot).map(([key, value]) => (
                <div key={key} className="mb-1">
                  <span className="font-medium text-slate-600">{humanize(key)}: </span>
                  <span className="whitespace-pre-line text-slate-700">{Array.isArray(value) ? value.join(", ") : String(value || "—")}</span>
                </div>
              ))}
            </li>
          ))}
        </ol>
      )}
    </Modal>
  );
}
