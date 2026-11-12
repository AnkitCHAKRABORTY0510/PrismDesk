import { useState } from "react";

import { ErrorMessage, Tabs } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { can } from "../../lib/permissions";
import {
  adminDashboard,
  guestDashboard,
  professorDashboard,
  studentDashboard,
  type DayCount,
  type DeadlineItem,
} from "../../services/dashboardService";
import PendingRegistrations from "../admin/PendingRegistrations";
import "./dashboard.css";
import { daysSince, daysUntil, greeting, isoDay, relativeDay, urgencyTone, type Tone } from "./dashUtils";
import { KpiRow, Pill, type Kpi } from "./parts";
import {
  AccountsPanel,
  AuditPanel,
  DeadlinesPanel,
  HandbookFeedPanel,
  HandbookPanel,
  LibraryPanel,
  MemberReadingPanel,
  ProjectsPanel,
  QueuePanel,
  ReadingPanel,
  ReviewsPanel,
  TasksPanel,
} from "./widgets";

type View = "admin" | "professor" | "student" | "guest";

const VIEWS: { id: View; label: string; capability: string }[] = [
  { id: "admin", label: "Administrator", capability: "dashboard.admin" },
  { id: "professor", label: "Professor", capability: "dashboard.professor" },
  { id: "student", label: "Student", capability: "dashboard.student" },
  { id: "guest", label: "Guest", capability: "dashboard.guest" },
];

// One column on phones, two on tablets, a 12-column bento on desktops.
const GRID = "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-12";
// Two stacked columns (7 + 5) on desktops; panels keep their natural height.
const COLUMNS = "grid grid-cols-1 items-start gap-4 xl:grid-cols-12";

interface StatusPill {
  key: string;
  tone: Tone;
  text: string;
  to?: string;
}

export default function Dashboard() {
  const { user } = useAuth();
  const available = VIEWS.filter((view) => can(user, view.capability));
  const [picked, setView] = useState<View | null>(null);
  // Fall back to the first view the user can see (also while auth is loading).
  const view = available.find((v) => v.id === picked)?.id ?? available[0]?.id;

  return (
    <div className="space-y-5">
      {available.length > 1 && view && <Tabs tabs={available} active={view} onChange={setView} />}
      {view === "admin" && <AdminView />}
      {view === "professor" && <ProfessorView />}
      {view === "student" && <StudentView />}
      {view === "guest" && <GuestView />}
    </div>
  );
}

/** Compact status-first header: greeting, date and up to three status pills. */
function Header({ name, pills }: { name: string; pills: StatusPill[] }) {
  const now = new Date();
  const first = name.trim().split(/\s+/)[0] ?? "";
  return (
    <header className="dash-in flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0">
        <p className="text-xs text-fg-muted">{now.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}</p>
        <h1 className="mt-0.5 text-xl font-semibold tracking-[-0.01em] text-fg">
          {greeting(now)}
          {first ? `, ${first}` : ""}
        </h1>
      </div>
      {pills.length > 0 && (
        <ul aria-label="Status" className="flex flex-wrap gap-2">
          {pills.slice(0, 3).map((pill) => (
            <li key={pill.key}>
              <Pill tone={pill.tone} to={pill.to}>
                {pill.text}
              </Pill>
            </li>
          ))}
        </ul>
      )}
    </header>
  );
}

function nextDeadlinePill(items: DeadlineItem[]): StatusPill | null {
  const now = new Date();
  const next = items.find((item) => daysUntil(item.due_at, now) >= 0);
  if (!next) return null;
  const days = daysUntil(next.due_at, now);
  const title = next.title.length > 26 ? `${next.title.slice(0, 25)}…` : next.title;
  return {
    key: "deadline",
    tone: urgencyTone(days),
    text: `${title} ${relativeDay(days)}`,
    to: next.kind === "task" ? `/tasks/${next.id}` : `/conferences?highlight=${next.id}`,
  };
}

const pills = (items: (StatusPill | null | false | undefined)[]) => items.filter(Boolean) as StatusPill[];

/** Daily counts for the last ``days`` days (oldest first), for sparklines. */
function series(daysData: DayCount[], days = 14): number[] {
  const counts = new Map(daysData.map((d) => [d.day, d.count]));
  const out: number[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    out.push(counts.get(isoDay(date)) ?? 0);
  }
  return out;
}

const pct = (n: number, d: number) => (d ? Math.round((n / d) * 100) : 0);

function Skeleton() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading dashboard">
      <div className="skeleton h-12 w-72" />
      <div className="skeleton h-24" />
      <div className={GRID}>
        {["xl:col-span-7", "xl:col-span-5", "xl:col-span-5", "xl:col-span-7"].map((span) => (
          <div key={span} className={`skeleton h-56 ${span}`} />
        ))}
      </div>
    </div>
  );
}

function StudentView() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(studentDashboard, []);
  if (loading && !data) return <Skeleton />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  const now = new Date();
  const tasks = data.assigned_tasks;
  const done = tasks.counts.completed ?? 0;
  const dueThisWeek = data.upcoming_deadlines.filter((d) => d.kind === "task" && daysUntil(d.due_at, now) <= 7).length;
  const reading = data.reading_progress;
  const kpis: Kpi[] = [
    { label: "Task completion", value: `${pct(done, tasks.total)}%`, detail: `${done} of ${tasks.total} approved`, ratio: tasks.total ? done / tasks.total : 0, to: "/tasks" },
    { label: "Open tasks", value: data.pending_submissions, detail: dueThisWeek ? `${dueThisWeek} due this week` : "nothing due this week", to: "/tasks?view=mine" },
    {
      label: "Papers read",
      value: reading.counts.completed ?? 0,
      detail: `of ${reading.total} · ${reading.counts.reading ?? 0} in progress`,
      ratio: reading.total ? (reading.counts.completed ?? 0) / reading.total : 0,
      to: "/research",
    },
    {
      label: "Handbook",
      value: data.handbook_entries_last_7_days,
      detail: `entries this week · ${data.handbook_streak}-day streak`,
      series: series(data.handbook_days),
      to: "/handbook",
    },
  ];
  const status = pills([
    (tasks.counts.revision_required ?? 0) > 0 && {
      key: "revise",
      tone: "warn",
      text: `${tasks.counts.revision_required} needs revision`,
      to: "/tasks?view=mine&status=revision_required",
    },
    (data.open_reminders ?? 0) > 0 && { key: "reminders", tone: "accent", text: `${data.open_reminders} open reminder${data.open_reminders === 1 ? "" : "s"}`, to: "/tasks?view=reminders" },
    nextDeadlinePill(data.upcoming_deadlines),
  ]);

  return (
    <div className="space-y-5">
      <Header name={user?.full_name ?? ""} pills={status} />
      <KpiRow items={kpis} />
      <div className={COLUMNS}>
        <DeadlinesPanel items={data.upcoming_deadlines} className="xl:col-span-7" />
        <div className="space-y-4 xl:col-span-5">
          <TasksPanel counts={tasks} personal={data.personal_tasks} />
          <HandbookPanel
            days={data.handbook_days}
            streak={data.handbook_streak}
            last30={data.handbook_entries_last_30_days}
            recent={data.recent_handbook_entries}
          />
        </div>
      </div>
      <ReadingPanel counts={reading} items={data.reading_list} canTrack={can(user, "research.track_progress")} />
      <ProjectsPanel title="My projects" projects={data.joined_projects} />
    </div>
  );
}

function ProfessorView() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(professorDashboard, []);
  if (loading && !data) return <Skeleton />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  const oldest = data.review_queue[0]?.submitted_at;
  const oldestAge = oldest ? daysSince(oldest) : 0;
  const overdue = data.supervised_projects.reduce((sum, p) => sum + p.overdue, 0);
  const members = data.reading_progress;
  const kpis: Kpi[] = [
    {
      label: "Waiting for review",
      value: data.pending_reviews,
      detail: data.pending_reviews ? `oldest ${oldestAge === 0 ? "from today" : `${oldestAge}d ago`}` : "inbox zero",
      to: "/tasks?view=reviews",
    },
    { label: "Overdue assignments", value: overdue, detail: "across your projects", to: "/tasks?view=managed&overdue=1" },
    { label: "Members", value: data.member_count, detail: `in ${data.supervised_projects.length} project${data.supervised_projects.length === 1 ? "" : "s"}`, to: "/projects" },
    {
      label: "Members' reading",
      value: `${pct(members.counts.completed ?? 0, members.total)}%`,
      detail: `${members.counts.completed ?? 0} of ${members.total} completed`,
      ratio: members.total ? (members.counts.completed ?? 0) / members.total : 0,
    },
  ];
  const status = pills([
    overdue > 0 && { key: "overdue", tone: "danger", text: `${overdue} overdue`, to: "/tasks?view=managed&overdue=1" },
    data.pending_reviews > 0 && {
      key: "reviews",
      tone: oldestAge >= 3 ? "warn" : "neutral",
      text: `${data.pending_reviews} review${data.pending_reviews === 1 ? "" : "s"} waiting`,
      to: "/tasks?view=reviews",
    },
    (data.open_reminders ?? 0) > 0 && { key: "reminders", tone: "accent", text: `${data.open_reminders} reminder${data.open_reminders === 1 ? "" : "s"}`, to: "/tasks?view=reminders" },
    nextDeadlinePill(data.upcoming_deadlines),
  ]);

  return (
    <div className="space-y-5">
      <Header name={user?.full_name ?? ""} pills={status} />
      <KpiRow items={kpis} />
      <div className={COLUMNS}>
        <div className="space-y-4 xl:col-span-7">
          <ReviewsPanel items={data.review_queue} total={data.pending_reviews} />
          <MemberReadingPanel rows={data.member_reading} />
        </div>
        <DeadlinesPanel items={data.upcoming_deadlines} className="xl:col-span-5" />
      </div>
      <ProjectsPanel title="Supervised projects" projects={data.supervised_projects} showPipeline showReviews />
      <div className={COLUMNS}>
        <ReadingPanel counts={data.my_reading} items={data.reading_list} canTrack={can(user, "research.track_progress")} title="My reading list" className="xl:col-span-7" />
        <HandbookFeedPanel items={data.recent_handbook_entries} className="xl:col-span-5" />
      </div>
    </div>
  );
}

function AdminView() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(adminDashboard, []);
  if (loading && !data) return <Skeleton />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  const failed = data.notifications.counts.failed ?? 0;
  const pending = data.users.counts.pending ?? 0;
  const hasReading = data.my_reading.total > 0 || data.reading_list.length > 0;
  const kpis: Kpi[] = [
    { label: "Active users", value: data.users.counts.approved ?? 0, detail: `${pending} pending approval`, to: "/admin/users" },
    { label: "Active projects", value: data.projects.counts.active ?? 0, detail: `${data.projects.counts.archived ?? 0} archived`, to: "/projects" },
    { label: "Research papers", value: data.research_papers, detail: "in the lab library", to: "/research" },
    { label: "Overdue assignments", value: data.overdue_assignments, detail: "official tasks", to: "/tasks?view=managed&overdue=1" },
  ];
  const status = pills([
    pending > 0 && { key: "pending", tone: "warn", text: `${pending} registration${pending === 1 ? "" : "s"} to approve` },
    failed > 0 && { key: "failed", tone: "danger", text: `${failed} failed notification${failed === 1 ? "" : "s"}` },
    data.overdue_assignments > 0 && { key: "overdue", tone: "danger", text: `${data.overdue_assignments} overdue`, to: "/tasks?view=managed&overdue=1" },
    nextDeadlinePill(data.upcoming_conferences),
  ]);

  return (
    <div className="space-y-5">
      <Header name={user?.full_name ?? ""} pills={status} />
      <KpiRow items={kpis} />
      <div className={GRID}>
        {pending > 0 && (
          <div className="dash-in min-w-0 md:col-span-2 xl:col-span-12">
            <PendingRegistrations onChange={reload} />
          </div>
        )}
        <TasksPanel title="Official tasks" counts={data.tasks} overdue={data.overdue_assignments} view="managed" className="xl:col-span-7" />
        <AccountsPanel users={data.users} projects={data.projects} className="xl:col-span-5" />
        <AuditPanel items={data.recent_activity} className="md:col-span-2 xl:col-span-7 xl:row-span-2" />
        <QueuePanel notifications={data.notifications} className="xl:col-span-5" />
        <DeadlinesPanel title="Conference deadlines" items={data.upcoming_conferences} className="xl:col-span-5" />
        {hasReading && (
          <ReadingPanel counts={data.my_reading} items={data.reading_list} canTrack={can(user, "research.track_progress")} className="md:col-span-2 xl:col-span-12" />
        )}
      </div>
    </div>
  );
}

function GuestView() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(guestDashboard, []);
  if (loading && !data) return <Skeleton />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  const next = data.upcoming_conferences.find((c) => daysUntil(c.due_at) >= 0);
  const kpis: Kpi[] = [
    { label: "Projects shared with you", value: data.projects.length, detail: "read-only access", to: "/projects" },
    { label: "Papers", value: data.paper_count, detail: "in those projects" },
    { label: "Next conference", value: next ? relativeDay(daysUntil(next.due_at)) : "—", detail: next?.title ?? "none scheduled" },
  ];

  return (
    <div className="space-y-5">
      <Header name={user?.full_name ?? ""} pills={pills([nextDeadlinePill(data.upcoming_conferences)])} />
      <KpiRow items={kpis} />
      <div className={GRID}>
        <DeadlinesPanel title="Conference deadlines" items={data.upcoming_conferences} className="md:col-span-2 xl:col-span-7" />
        <LibraryPanel count={data.paper_count} className="md:col-span-2 xl:col-span-5" />
        <ProjectsPanel title="Projects" projects={data.projects} emptyText="No projects have been shared with you yet." className="md:col-span-2 xl:col-span-12" />
      </div>
    </div>
  );
}
