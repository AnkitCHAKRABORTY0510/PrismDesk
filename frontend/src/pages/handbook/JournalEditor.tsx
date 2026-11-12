import { useEffect, useRef, useState } from "react";
import { History, PenLine } from "lucide-react";

import { Alert, Button } from "../../components/ui";
import { wordCount, type ISODate } from "../../lib/calendar";
import { formatDateTime } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { createSummary, summaryVersions, updateSummary, type DailySummary } from "../../services/handbookService";
import { RULED, SUMMARY_FIELDS, draftKey, readStorage, writeStorage } from "./plannerMeta";
import { VersionHistory } from "./VersionHistory";

interface Draft {
  summary: string;
  challenges: string;
  plan_next: string;
  saved_at: string;
}

const EMPTY = { summary: "", challenges: "", plan_next: "" };

function readDraft(key: string): Draft | null {
  const raw = readStorage(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Draft;
  } catch {
    return null;
  }
}

// The private "what I did today" journal for one day (a DailySummary).
// Opens in read mode when the day has a journal; editing keeps a local
// draft on this device until it is saved through the summaries API (which
// records a new version each time).
export function JournalEditor({
  day,
  userId,
  summary,
  onSaved,
  onDirtyChange,
  onOpenChild,
}: {
  day: ISODate;
  userId: string;
  summary: DailySummary | null;
  onSaved: (summary: DailySummary) => void;
  onDirtyChange: (dirty: boolean) => void;
  onOpenChild: (open: boolean) => void;
}) {
  const key = draftKey(userId, day);
  const saved = summary ? { summary: summary.summary, challenges: summary.challenges, plan_next: summary.plan_next } : EMPTY;
  const [editing, setEditing] = useState(() => !summary || readDraft(key) !== null);
  const [fields, setFields] = useState(() => {
    const draft = readDraft(key);
    return draft ? { summary: draft.summary, challenges: draft.challenges, plan_next: draft.plan_next } : saved;
  });
  const [restoredAt, setRestoredAt] = useState(() => readDraft(key)?.saved_at ?? "");
  const [draftSavedAt, setDraftSavedAt] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const dirty = editing && (fields.summary !== saved.summary || fields.challenges !== saved.challenges || fields.plan_next !== saved.plan_next);

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  // Autosave a local draft shortly after typing stops.
  useEffect(() => {
    if (!dirty) return;
    const timer = window.setTimeout(() => {
      const at = new Date().toISOString();
      writeStorage(key, JSON.stringify({ ...fields, saved_at: at }));
      setDraftSavedAt(at);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [dirty, fields, key]);

  // Leaving the site with unsaved text asks first (the draft is kept anyway).
  useEffect(() => {
    if (!dirty) return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const startEditing = () => {
    setFields(saved);
    setEditing(true);
    window.setTimeout(() => textRef.current?.focus(), 0);
  };

  const discard = () => {
    writeStorage(key, null);
    setRestoredAt("");
    setDraftSavedAt("");
    setFields(saved);
    setEditing(!summary);
  };

  const save = async () => {
    if (!fields.summary.trim()) {
      setError("Write at least a line about the day before saving.");
      textRef.current?.focus();
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = summary
        ? await updateSummary(summary.id, fields)
        : await createSummary({ entry_date: day, ...fields });
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

  const words = wordCount(`${fields.summary} ${fields.challenges} ${fields.plan_next}`);
  const openHistory = (open: boolean) => {
    setHistory(open);
    onOpenChild(open);
  };

  const meta = (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-muted">
      <span>{words} {words === 1 ? "word" : "words"}</span>
      {summary && <span>Saved {formatDateTime(summary.updated_at)} · version {summary.version}</span>}
      {!summary && !dirty && <span>Not written yet</span>}
      {dirty && <span className="text-warn-fg">Unsaved changes{draftSavedAt ? ` · draft kept on this device ${new Date(draftSavedAt).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}` : ""}</span>}
    </div>
  );

  if (!editing && summary) {
    return (
      <section aria-label="Journal" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {meta}
          <div className="flex gap-2">
            {summary.version > 1 && (
              <Button size="sm" variant="ghost" onClick={() => openHistory(true)}>
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                History
              </Button>
            )}
            <Button size="sm" onClick={startEditing}>
              <PenLine className="h-3.5 w-3.5" aria-hidden="true" />
              Edit
            </Button>
          </div>
        </div>
        <div className="space-y-5 border-l-2 border-danger-line pl-4 sm:pl-6">
          {SUMMARY_FIELDS.map(([field, label]) => {
            const value = summary[field];
            if (!value && field !== "summary") return null;
            return (
              <div key={field}>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-fg-muted">{label}</h3>
                <p className="whitespace-pre-line font-serif text-[1.05rem] text-fg" style={RULED}>{value}</p>
              </div>
            );
          })}
        </div>
        {history && (
          <VersionHistory
            title="Journal history"
            load={() => summaryVersions(summary.id)}
            fields={SUMMARY_FIELDS}
            onClose={() => openHistory(false)}
          />
        )}
      </section>
    );
  }

  return (
    <section aria-label="Journal" className="space-y-4">
      {restoredAt && (
        <Alert kind="info">
          <span className="flex flex-wrap items-center justify-between gap-2">
            <span>Restored your unsaved draft from {formatDateTime(restoredAt)}.</span>
            <button type="button" onClick={discard} className="text-xs font-medium underline underline-offset-2">Discard draft</button>
          </span>
        </Alert>
      )}
      <div className="space-y-4 border-l-2 border-danger-line pl-4 sm:pl-6">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-fg-muted">What I did today</span>
          <textarea
            ref={textRef}
            value={fields.summary}
            onChange={(e) => setFields({ ...fields, summary: e.target.value })}
            placeholder="Dear handbook, today I…"
            rows={7}
            className="mt-1 block w-full resize-y bg-transparent font-serif text-[1.05rem] text-fg outline-none placeholder:italic placeholder:text-fg-subtle focus-visible:outline-none"
            style={RULED}
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-fg-muted">Challenges</span>
            <textarea
              value={fields.challenges}
              onChange={(e) => setFields({ ...fields, challenges: e.target.value })}
              placeholder="What got in the way?"
              rows={3}
              className="mt-1 block w-full resize-y bg-transparent font-serif text-fg outline-none placeholder:italic placeholder:text-fg-subtle"
              style={RULED}
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-fg-muted">Plan for next day</span>
            <textarea
              value={fields.plan_next}
              onChange={(e) => setFields({ ...fields, plan_next: e.target.value })}
              placeholder="Tomorrow I will…"
              rows={3}
              className="mt-1 block w-full resize-y bg-transparent font-serif text-fg outline-none placeholder:italic placeholder:text-fg-subtle"
              style={RULED}
            />
          </label>
        </div>
      </div>
      {error && <Alert>{error}</Alert>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {meta}
        <div className="flex gap-2">
          {(summary || dirty) && (
            <Button size="sm" variant="secondary" onClick={discard} disabled={saving}>
              {summary ? "Cancel" : "Clear"}
            </Button>
          )}
          <Button size="sm" onClick={save} loading={saving} disabled={!dirty && !!summary}>
            Save journal
          </Button>
        </div>
      </div>
    </section>
  );
}
