import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";
import { CalendarDays, List } from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Alert,
  Button,
  Card,
  DataTable,
  EmptyState,
  ErrorMessage,
  Field,
  Input,
  Loading,
  Pagination,
  Select,
  Tabs,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { monthWeeks, sameMonth, today as todayDay, weekDays, wordCount, type ISODate } from "../../lib/calendar";
import { formatDate } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import { listEntries, listSharedNotes, listSummaries, progress } from "../../services/handbookService";
import { PLANNER_CHANGED, getPlanner, type Pin } from "../../services/handbookPlannerService";
import { listMembers, listProjects } from "../../services/projectService";
import { CalendarView, type CalendarMode } from "./CalendarView";
import { DayPage } from "./DayPage";
import EntryFormModal from "./EntryFormModal";
import { EMPTY_DAY, readStorage, writeStorage, type DayInfo } from "./plannerMeta";
import { SideRail } from "./SideRail";

type View = "calendar" | "entries" | "summaries";

const MODE_KEY = "prismdesk.handbook.calendarMode";
const isDay = (value: string | null): value is ISODate => !!value && /^\d{4}-\d{2}-\d{2}$/.test(value);

export default function Handbook() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const canWrite = can(user, "handbook.write");
  const requested = params.get("view");
  const view: View = requested === "entries" ? "entries" : requested === "summaries" && canWrite ? "summaries" : "calendar";

  const setView = (next: View) => {
    const updated = new URLSearchParams(params);
    if (next === "calendar") updated.delete("view");
    else updated.set("view", next);
    setParams(updated);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research Handbook"
        description={
          canWrite
            ? "Your research notebook: a private journal for every day, project entries for your supervisors, and a planner for what's ahead."
            : "Daily entries from the projects you supervise, plus your own planner."
        }
        actions={
          <div role="group" aria-label="Handbook view" className="flex rounded-lg border border-line-strong bg-surface p-0.5">
            <ViewButton active={view === "calendar"} onClick={() => setView("calendar")} icon={<CalendarDays className="h-4 w-4" aria-hidden="true" />}>
              Calendar
            </ViewButton>
            <ViewButton active={view !== "calendar"} onClick={() => setView("entries")} icon={<List className="h-4 w-4" aria-hidden="true" />}>
              List
            </ViewButton>
          </div>
        }
      />
      {view === "calendar" ? <CalendarHome canWrite={canWrite} userId={user?.id ?? ""} /> : <ListViews view={view} canWrite={canWrite} onView={setView} />}
    </div>
  );
}

function ViewButton({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: ReactNode; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`inline-flex h-9 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors ${
        active ? "bg-brand text-brand-fg shadow-sm" : "text-fg-muted hover:text-fg"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

// --- Calendar home ------------------------------------------------------------------

function CalendarHome({ canWrite, userId }: { canWrite: boolean; userId: string }) {
  const [params, setParams] = useSearchParams();
  const initialDay = params.get("day");
  const [focused, setFocused] = useState<ISODate>(isDay(initialDay) ? initialDay : todayDay());
  const [mode, setModeState] = useState<CalendarMode>(() => (readStorage(MODE_KEY) === "week" ? "week" : "month"));
  const openParam = params.get("open");
  const openDay = isDay(openParam) ? openParam : null;
  const [refreshKey, setRefreshKey] = useState(0);

  const setMode = (next: CalendarMode) => {
    setModeState(next);
    writeStorage(MODE_KEY, next);
  };

  const openDayPage = (day: ISODate | null) => {
    const updated = new URLSearchParams(params);
    if (day) {
      updated.set("open", day);
      setFocused(day);
    } else updated.delete("open");
    updated.delete("day");
    setParams(updated, { replace: !!day && !!openDay });
  };

  const weeks = mode === "month" ? monthWeeks(focused) : [weekDays(focused)];
  const rangeFrom = weeks[0][0];
  const rangeTo = weeks[weeks.length - 1][6];

  const data = useAsync(async () => {
    const [days, journals, planner, shared] = await Promise.all([
      progress({ date_from: rangeFrom, date_to: rangeTo }),
      canWrite ? listSummaries({ date_from: rangeFrom, date_to: rangeTo, page_size: 100 }) : Promise.resolve(null),
      // The planner is optional: if it fails, the journal calendar still loads.
      getPlanner(rangeFrom, rangeTo).then(
        (result) => ({ result, error: "" }),
        (err: unknown) => ({ result: { pins: [], todos: [], reminders: [] }, error: getErrorMessage(err) })
      ),
      // Shared notes are optional for the calendar too.
      listSharedNotes({ date_from: rangeFrom, date_to: rangeTo, page_size: 100 }).then(
        (page) => page.items,
        () => []
      ),
    ]);
    return { days, journals: journals?.items ?? [], planner: planner.result, plannerError: planner.error, shared };
  }, [rangeFrom, rangeTo, canWrite, refreshKey]);

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  // Planner changes made elsewhere (side rail, reminder "Done") refresh too.
  useEffect(() => {
    window.addEventListener(PLANNER_CHANGED, refresh);
    return () => window.removeEventListener(PLANNER_CHANGED, refresh);
  }, [refresh]);

  const days = useMemo(() => {
    const map = new Map<ISODate, DayInfo>();
    const get = (day: ISODate) => {
      let info = map.get(day);
      if (!info) {
        info = { ...EMPTY_DAY, pins: [], reminders: [], todos: [] };
        map.set(day, info);
      }
      return info;
    };
    if (!data.data) return map;
    for (const day of data.data.days) get(day.entry_date).entries = day.entry_count;
    for (const journal of data.data.journals) {
      const info = get(journal.entry_date);
      info.journalWords = wordCount(`${journal.summary} ${journal.challenges} ${journal.plan_next}`);
      info.journalSnippet = journal.summary.slice(0, 140);
    }
    for (const note of data.data.shared) get(note.entry_date).sharedNotes += 1;
    for (const pin of data.data.planner.pins) get(pin.pin_date).pins.push(pin);
    for (const reminder of data.data.planner.reminders) get(reminder.reminder_date).reminders.push(reminder);
    for (const todo of data.data.planner.todos) get(todo.todo_date).todos.push(todo);
    return map;
  }, [data.data]);

  const monthStats = useMemo(() => {
    let journalDays = 0;
    let entries = 0;
    const pins: Pin[] = [];
    for (const [day, info] of days) {
      // Month view counts the focused month; week view the visible week.
      if (mode === "month" && !sameMonth(day, focused)) continue;
      if (info.journalWords > 0) journalDays += 1;
      entries += info.entries;
      pins.push(...info.pins);
    }
    pins.sort((a, b) => a.pin_date.localeCompare(b.pin_date));
    return { journalDays, entries, pins };
  }, [days, focused, mode]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <Card className="min-w-0">
        <ErrorMessage message={data.error} onRetry={data.reload} />
        {data.data?.plannerError && (
          <div className="mb-4">
            <Alert kind="info">
              Pins, to-dos and reminders are unavailable right now ({data.data.plannerError}). Your journal and project entries still work.
            </Alert>
          </div>
        )}
        <CalendarView
          focused={focused}
          onFocus={setFocused}
          onOpen={openDayPage}
          mode={mode}
          onModeChange={setMode}
          days={days}
          loading={data.loading}
        />
      </Card>
      <SideRail
        canWrite={canWrite}
        period={mode}
        monthPins={monthStats.pins}
        monthJournalDays={monthStats.journalDays}
        monthEntries={monthStats.entries}
        refreshKey={refreshKey}
        onOpen={openDayPage}
      />
      {openDay && (
        <DayPage
          day={openDay}
          userId={userId}
          canWrite={canWrite}
          onNavigate={(day) => openDayPage(day)}
          onClose={() => openDayPage(null)}
          onChanged={refresh}
        />
      )}
    </div>
  );
}

// --- List views (the original tables) ----------------------------------------------

function ListViews({ view, canWrite, onView }: { view: View; canWrite: boolean; onView: (view: View) => void }) {
  return (
    <div className="space-y-6">
      {canWrite && (
        <Tabs
          tabs={[
            { id: "entries" as View, label: "Project entries" },
            { id: "summaries" as View, label: "My journal (private)" },
          ]}
          active={view}
          onChange={onView}
        />
      )}
      {view === "summaries" ? <JournalList /> : <EntryList canWrite={canWrite} />}
    </div>
  );
}

function EntryList({ canWrite }: { canWrite: boolean }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const canReview = can(user, "handbook.review");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [projectId, setProjectId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  const entries = useAsync(
    () => listEntries({ date_from: dateFrom, date_to: dateTo, project_id: projectId, student_id: studentId, page, page_size: 20 }),
    [dateFrom, dateTo, projectId, studentId, page]
  );
  const projects = useAsync(
    async () => (canReview ? (await listProjects({ page_size: 100 })).items.filter((p) => p.my_role === "supervisor" || p.my_role === "owner" || p.permissions.can_review) : []),
    [canReview]
  );
  const members = useAsync(
    async () => (canReview && projectId ? (await listMembers(projectId)).filter((m) => m.membership_role === "owner" || m.membership_role === "member") : []),
    [canReview, projectId]
  );
  const filtered = !!(dateFrom || dateTo || projectId || studentId);
  const reset = (apply: () => void) => {
    apply();
    setPage(1);
  };

  return (
    <Card
      title="Project entries"
      actions={canWrite && <Button onClick={() => setCreating(true)}>New project entry</Button>}
    >
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="From">{(id) => <Input id={id} type="date" value={dateFrom} onChange={(e) => reset(() => setDateFrom(e.target.value))} />}</Field>
        <Field label="To">{(id) => <Input id={id} type="date" value={dateTo} onChange={(e) => reset(() => setDateTo(e.target.value))} />}</Field>
        {canReview && (
          <>
            <Field label="Project">
              {(id) => (
                <Select id={id} value={projectId} onChange={(e) => reset(() => { setProjectId(e.target.value); setStudentId(""); })}>
                  <option value="">All supervised projects</option>
                  {(projects.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                </Select>
              )}
            </Field>
            <Field label="Student" hint={projectId ? undefined : "Pick a project first."}>
              {(id) => (
                <Select id={id} value={studentId} disabled={!projectId} onChange={(e) => reset(() => setStudentId(e.target.value))}>
                  <option value="">All students</option>
                  {(members.data ?? []).map((m) => <option key={m.user.id} value={m.user.id}>{m.user.full_name}</option>)}
                </Select>
              )}
            </Field>
          </>
        )}
      </div>
      <ErrorMessage message={entries.error} onRetry={entries.reload} />
      {entries.loading && !entries.data ? (
        <Loading />
      ) : entries.data && entries.data.items.length === 0 ? (
        <EmptyState
          title={filtered ? "No entries match these filters" : "No handbook entries yet"}
          description={
            filtered
              ? "Try a wider date range or clear the filters."
              : canWrite
                ? "Write a project entry at the end of each working day so your supervisors can follow along."
                : "Entries from the projects you supervise will appear here."
          }
          action={
            filtered ? (
              <Button variant="secondary" onClick={() => reset(() => { setDateFrom(""); setDateTo(""); setProjectId(""); setStudentId(""); })}>Clear filters</Button>
            ) : canWrite ? (
              <Button onClick={() => setCreating(true)}>Write today's entry</Button>
            ) : undefined
          }
        />
      ) : (
        entries.data && (
          <>
            <DataTable
              rows={entries.data.items}
              rowKey={(row) => row.id}
              columns={[
                { header: "Date", cell: (row) => <Link className="font-medium hover:text-link" to={`/handbook/entries/${row.id}`}>{formatDate(row.entry_date)}</Link> },
                { header: "Project", cell: (row) => row.project_title },
                { header: "Student", cell: (row) => row.student.full_name },
                { header: "Summary", cell: (row) => <span className="line-clamp-2 text-fg-soft">{row.work_completed || row.research_progress}</span> },
                { header: "Version", cell: (row) => `v${row.version}` },
                { header: "Comments", cell: (row) => row.comment_count },
              ]}
            />
            <Pagination page={page} pageSize={20} total={entries.data.total} onChange={setPage} />
          </>
        )
      )}
      {creating && (
        <EntryFormModal
          open
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            notify("Entry saved.");
            void entries.reload();
          }}
        />
      )}
    </Card>
  );
}

function JournalList() {
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [params, setParams] = useSearchParams();
  const summaries = useAsync(() => listSummaries({ date_from: dateFrom, date_to: dateTo, page, page_size: 20 }), [dateFrom, dateTo, page]);

  // Rows open the day page in the calendar, where the journal is edited.
  const openDay = (day: ISODate) => {
    const updated = new URLSearchParams(params);
    updated.delete("view");
    updated.set("open", day);
    setParams(updated);
  };

  return (
    <Card title="My journal" actions={<Button onClick={() => openDay(todayDay())}>Write today's page</Button>}>
      <p className="mb-4 text-xs text-fg-muted">Your journal is private: professors and administrators cannot see it.</p>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:max-w-md">
        <Field label="From">{(id) => <Input id={id} type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} />}</Field>
        <Field label="To">{(id) => <Input id={id} type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} />}</Field>
      </div>
      <ErrorMessage message={summaries.error} onRetry={summaries.reload} />
      {summaries.loading && !summaries.data ? (
        <Loading />
      ) : summaries.data && summaries.data.items.length === 0 ? (
        <EmptyState
          title="No journal pages yet"
          description="A few lines a day about what you did, what got in the way and what's next. Only you can read it."
          action={<Button onClick={() => openDay(todayDay())}>Start today's page</Button>}
        />
      ) : (
        summaries.data && (
          <>
            <DataTable
              rows={summaries.data.items}
              rowKey={(row) => row.id}
              onRowClick={(row) => openDay(row.entry_date)}
              columns={[
                { header: "Date", cell: (row) => formatDate(row.entry_date) },
                { header: "Summary", cell: (row) => <span className="line-clamp-2">{row.summary}</span> },
                { header: "Words", cell: (row) => wordCount(`${row.summary} ${row.challenges} ${row.plan_next}`) },
                { header: "Version", cell: (row) => `v${row.version}` },
              ]}
            />
            <Pagination page={page} pageSize={20} total={summaries.data.total} onChange={setPage} />
          </>
        )
      )}
    </Card>
  );
}
