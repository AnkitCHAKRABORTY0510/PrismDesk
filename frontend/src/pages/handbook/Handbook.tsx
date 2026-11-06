import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Alert,
  Button,
  Card,
  DataTable,
  ErrorMessage,
  Field,
  Input,
  Loading,
  Modal,
  Pagination,
  Tabs,
  Textarea,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { formatDate, todayLocal } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import {
  createSummary,
  listEntries,
  listSummaries,
  progress,
  updateSummary,
  type DailySummary,
} from "../../services/handbookService";
import EntryFormModal from "./EntryFormModal";

type View = "entries" | "summaries";

export default function Handbook() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [params, setParams] = useSearchParams();
  const canWrite = can(user, "handbook.write");
  const view: View = canWrite && params.get("view") === "summaries" ? "summaries" : "entries";
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  const entries = useAsync(
    () => listEntries({ date_from: dateFrom, date_to: dateTo, page, page_size: 20 }),
    [dateFrom, dateTo, page]
  );
  const days = useAsync(() => progress({}), []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research Handbook"
        description={canWrite ? "Record daily progress per project, plus a private overall summary." : "Daily entries from the projects you supervise."}
        actions={canWrite && view === "entries" && <Button onClick={() => setCreating(true)}>New daily entry</Button>}
      />
      {canWrite && (
        <Tabs
          tabs={[
            { id: "entries" as View, label: "Project entries" },
            { id: "summaries" as View, label: "Overall daily summaries (private)" },
          ]}
          active={view}
          onChange={(next) => setParams({ view: next })}
        />
      )}

      {view === "summaries" ? (
        <Summaries />
      ) : (
        <>
          <Card title="Activity in the last 30 days">
            {days.data && days.data.length > 0 ? (
              <div className="flex flex-wrap gap-1" aria-label="Entries per day">
                {days.data.map((day) => (
                  <span
                    key={day.entry_date}
                    title={`${formatDate(day.entry_date)}: ${day.entry_count} entries by ${day.student_count} student(s)`}
                    className="rounded bg-brand/10 px-2 py-1 text-xs text-brand"
                  >
                    {day.entry_date.slice(5)} · {day.entry_count}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No entries in the last 30 days.</p>
            )}
          </Card>
          <Card
            actions={
              <div className="flex gap-2">
                <Input aria-label="From date" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} />
                <Input aria-label="To date" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} />
              </div>
            }
            title="Entries"
          >
            <ErrorMessage message={entries.error} onRetry={entries.reload} />
            {entries.loading && !entries.data ? (
              <Loading />
            ) : (
              entries.data && (
                <>
                  <DataTable
                    rows={entries.data.items}
                    rowKey={(row) => row.id}
                    empty="No handbook entries yet."
                    columns={[
                      { header: "Date", cell: (row) => <Link className="font-medium hover:text-brand" to={`/handbook/entries/${row.id}`}>{formatDate(row.entry_date)}</Link> },
                      { header: "Project", cell: (row) => row.project_title },
                      { header: "Student", cell: (row) => row.student.full_name },
                      { header: "Summary", cell: (row) => <span className="line-clamp-2 text-slate-600">{row.work_completed || row.research_progress}</span> },
                      { header: "Version", cell: (row) => `v${row.version}` },
                      { header: "Comments", cell: (row) => row.comment_count },
                    ]}
                  />
                  <Pagination page={page} pageSize={20} total={entries.data.total} onChange={setPage} />
                </>
              )
            )}
          </Card>
        </>
      )}

      {creating && (
        <EntryFormModal
          open
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            notify("Entry saved.");
            void entries.reload();
            void days.reload();
          }}
        />
      )}
    </div>
  );
}

function Summaries() {
  const { notify } = useToast();
  const [page, setPage] = useState(1);
  const summaries = useAsync(() => listSummaries({ page, page_size: 20 }), [page]);
  const [editing, setEditing] = useState<DailySummary | "new" | null>(null);

  return (
    <Card
      title="My overall daily summaries"
      actions={<Button onClick={() => setEditing("new")}>New summary</Button>}
    >
      <p className="mb-4 text-xs text-slate-500">Overall summaries are private: professors and administrators cannot see them.</p>
      <ErrorMessage message={summaries.error} onRetry={summaries.reload} />
      {summaries.loading && !summaries.data ? (
        <Loading />
      ) : (
        summaries.data && (
          <>
            <DataTable
              rows={summaries.data.items}
              rowKey={(row) => row.id}
              empty="No summaries yet."
              onRowClick={(row) => setEditing(row)}
              columns={[
                { header: "Date", cell: (row) => formatDate(row.entry_date) },
                { header: "Summary", cell: (row) => <span className="line-clamp-2">{row.summary}</span> },
                { header: "Version", cell: (row) => `v${row.version}` },
              ]}
            />
            <Pagination page={page} pageSize={20} total={summaries.data.total} onChange={setPage} />
          </>
        )
      )}
      {editing && (
        <SummaryModal
          summary={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            notify("Summary saved.");
            void summaries.reload();
          }}
        />
      )}
    </Card>
  );
}

function SummaryModal({ summary, onClose, onSaved }: { summary: DailySummary | null; onClose: () => void; onSaved: () => void }) {
  const [date, setDate] = useState(summary?.entry_date ?? todayLocal());
  const [text, setText] = useState(summary?.summary ?? "");
  const [challenges, setChallenges] = useState(summary?.challenges ?? "");
  const [plan, setPlan] = useState(summary?.plan_next ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (summary) await updateSummary(summary.id, { summary: text, challenges, plan_next: plan });
      else await createSummary({ entry_date: date, summary: text, challenges, plan_next: plan });
      onSaved();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      title={summary ? `Summary for ${formatDate(summary.entry_date)}` : "New overall daily summary"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="summary-form" loading={saving}>Save</Button>
        </>
      }
    >
      <form id="summary-form" onSubmit={submit} className="space-y-4">
        {!summary && <Field label="Date">{(id) => <Input id={id} type="date" max={todayLocal()} value={date} onChange={(e) => setDate(e.target.value)} />}</Field>}
        <Field label="Summary">{(id) => <Textarea id={id} required value={text} onChange={(e) => setText(e.target.value)} />}</Field>
        <Field label="Challenges">{(id) => <Textarea id={id} rows={2} value={challenges} onChange={(e) => setChallenges(e.target.value)} />}</Field>
        <Field label="Plan for next day">{(id) => <Textarea id={id} rows={2} value={plan} onChange={(e) => setPlan(e.target.value)} />}</Field>
        {error && <Alert>{error}</Alert>}
      </form>
    </Modal>
  );
}
