import { useState, type ReactNode } from "react";
import { Link } from "react-router";

import { GithubMark } from "../../components/common/GithubMark";
import { ReadingStatusToggle } from "../../components/research/ReadingStatusToggle";
import { formatDate, formatDateTime, humanize } from "../../lib/format";
import { repoName } from "../../lib/github";
import { READING_STATES } from "../../lib/reading";
import type {
  ActivityItem,
  CountMap,
  DayCount,
  DeadlineItem,
  HandbookItem,
  MemberReading,
  ProjectSummaryItem,
  ReadingListItem,
  ReviewItem,
} from "../../services/dashboardService";
import type { ReadingStatus } from "../../services/researchService";
import {
  READING_COLORS,
  STAGES,
  TONE_DOT,
  TONE_TEXT,
  accentMix,
  daysSince,
  daysUntil,
  isoDay,
  relativeDay,
  urgencyTone,
  type Tone,
} from "./dashUtils";
import { Avatar, AvatarStack, Empty, Panel, Progress, StackedBar } from "./parts";

interface Placement {
  className?: string;
}

const deadlineHref = (item: DeadlineItem) => (item.kind === "task" ? `/tasks/${item.id}` : `/conferences?highlight=${item.id}`);

// --- Deadlines ----------------------------------------------------------------------

const WINDOW = 30;

function DeadlineStrip({ items, now }: { items: DeadlineItem[]; now: Date }) {
  const ticks = items
    .map((item) => ({ item, days: daysUntil(item.due_at, now) }))
    .filter(({ days }) => days >= 0 && days <= WINDOW);
  return (
    <div className="px-4 pt-4 pb-1" aria-hidden="true">
      <div className="relative h-5">
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-line-strong" />
        {[0, 7, 14, 21, 28].map((d) => (
          <span key={d} className="absolute top-1/2 h-2 w-px -translate-y-1/2 bg-line-strong" style={{ left: `${(d / WINDOW) * 100}%` }} />
        ))}
        {ticks.map(({ item, days }, i) => {
          const tone = i === 0 ? urgencyTone(days) : "neutral";
          return (
            <span
              key={`${item.kind}-${item.id}`}
              title={`${item.title} · ${relativeDay(days)}`}
              className={`absolute top-1/2 h-3 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full ${tone === "neutral" ? "bg-brand" : TONE_DOT[tone]}`}
              style={{ left: `${(days / WINDOW) * 100}%` }}
            />
          );
        })}
      </div>
      <div className="mt-1 flex justify-between text-[10px] tabular-nums text-fg-subtle">
        <span>Today</span>
        <span>+1w</span>
        <span>+2w</span>
        <span>+3w</span>
        <span>+4w</span>
      </div>
    </div>
  );
}

export function DeadlinesPanel({
  title = "Upcoming deadlines",
  items,
  emptyText = "Nothing due in the next weeks.",
  className = "",
}: { title?: string; items: DeadlineItem[]; emptyText?: string } & Placement) {
  const now = new Date();
  const upcoming = items.filter((item) => daysUntil(item.due_at, now) >= 0);
  const shown = upcoming.slice(0, 6);
  return (
    <Panel title={title} meta={upcoming.length || undefined} action={{ to: "/conferences", label: "Calendar" }} className={className} bodyClassName="">
      {upcoming.length === 0 ? (
        <Empty>{emptyText}</Empty>
      ) : (
        <>
          <DeadlineStrip items={upcoming} now={now} />
          <ul className="divide-y divide-line">
            {shown.map((item, i) => {
              const days = daysUntil(item.due_at, now);
              const tone: Tone = i === 0 ? urgencyTone(days) : days <= 2 ? "danger" : "neutral";
              const due = new Date(item.due_at);
              return (
                <li key={`${item.kind}-${item.id}`}>
                  <Link
                    to={deadlineHref(item)}
                    className="grid grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 transition-colors duration-150 hover:bg-surface-muted"
                  >
                    <span className="text-center leading-none">
                      <span className="block text-[10px] font-medium uppercase tracking-[0.04em] text-fg-subtle">
                        {due.toLocaleDateString(undefined, { month: "short" })}
                      </span>
                      <span className="mt-0.5 block text-base font-semibold tabular-nums text-fg">{due.getDate()}</span>
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-fg">{item.title}</span>
                      <span className="block truncate text-xs text-fg-muted">
                        {item.kind === "task" ? "Task" : "Conference"}
                        {item.project_title ? ` · ${item.project_title}` : ""}
                      </span>
                    </span>
                    <span className={`flex items-center gap-1.5 text-xs whitespace-nowrap tabular-nums ${TONE_TEXT[tone]}`}>
                      {tone !== "neutral" && <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]}`} aria-hidden="true" />}
                      {relativeDay(days)}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
          {upcoming.length > shown.length && (
            <p className="border-t border-line px-4 py-2 text-xs text-fg-muted">+{upcoming.length - shown.length} later</p>
          )}
        </>
      )}
    </Panel>
  );
}

// --- Tasks ---------------------------------------------------------------------------

export function TasksPanel({
  title = "Tasks",
  counts,
  overdue,
  personal,
  view = "mine",
  className = "",
}: { title?: string; counts: CountMap; overdue?: number; personal?: CountMap; view?: string } & Placement) {
  const segments = STAGES.map((stage) => ({
    key: stage.key,
    label: stage.label,
    color: stage.color,
    value: counts.counts[stage.key] ?? 0,
    to: `/tasks?view=${view}&status=${stage.key}`,
  }));
  return (
    <Panel title={title} meta={counts.total || undefined} action={{ to: `/tasks?view=${view}`, label: "All tasks" }} className={className}>
      {counts.total === 0 ? (
        <Empty>No official tasks yet.</Empty>
      ) : (
        <>
          <StackedBar segments={segments} label={title} />
          {overdue ? (
            <Link to={`/tasks?view=${view}&overdue=1`} className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-danger-fg hover:underline">
              <span className="h-1.5 w-1.5 rounded-full bg-danger" aria-hidden="true" />
              {overdue} overdue
            </Link>
          ) : null}
        </>
      )}
      {personal && personal.total > 0 && (
        <div className="mt-4 border-t border-line pt-4">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-medium text-fg-soft">Personal</span>
            <Link to="/tasks?view=personal" className="text-fg-muted transition-colors duration-150 hover:text-fg">
              Open →
            </Link>
          </div>
          <StackedBar
            label="Personal tasks"
            segments={[
              { key: "todo", label: "To do", value: personal.counts.todo ?? 0, color: "var(--line-strong)", to: "/tasks?view=personal&status=todo" },
              { key: "in_progress", label: "In progress", value: personal.counts.in_progress ?? 0, color: "var(--primary)", to: "/tasks?view=personal&status=in_progress" },
              { key: "completed", label: "Done", value: personal.counts.completed ?? 0, color: "var(--success)", to: "/tasks?view=personal&status=completed" },
            ]}
          />
        </div>
      )}
    </Panel>
  );
}

// --- Handbook --------------------------------------------------------------------------

const WEEKS = 15;

export function HandbookPanel({
  days,
  streak,
  last30,
  recent,
  className = "",
}: { days: DayCount[]; streak: number; last30: number; recent: HandbookItem[] } & Placement) {
  const counts = new Map(days.map((d) => [d.day, d.count]));
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const weekday = (today.getDay() + 6) % 7;
  const start = new Date(today);
  start.setDate(today.getDate() - ((WEEKS - 1) * 7 + weekday));
  const cells = Array.from({ length: WEEKS * 7 }, (_, i) => {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    const key = isoDay(date);
    return { key, count: counts.get(key) ?? 0, future: date > today };
  });
  const level = (n: number) => (n === 0 ? "var(--track)" : accentMix(n === 1 ? 40 : n === 2 ? 65 : 100));

  return (
    <Panel title="Handbook" meta={`${last30} entries in 30 days`} action={{ to: "/handbook", label: "Open" }} className={className}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div
          role="img"
          aria-label={`Handbook activity: ${last30} entries in the last 30 days, ${streak}-day streak`}
          className="grid grid-flow-col grid-rows-7 gap-[3px]"
        >
          {cells.map((cell) => (
            <span
              key={cell.key}
              title={cell.future ? undefined : `${formatDate(cell.key)}: ${cell.count} ${cell.count === 1 ? "entry" : "entries"}`}
              className={`h-[11px] w-[11px] rounded-[2px] ${cell.future ? "invisible" : ""}`}
              style={{ background: level(cell.count) }}
            />
          ))}
        </div>
        <div className="text-right">
          <div className="text-2xl leading-none font-semibold tracking-[-0.02em] tabular-nums text-fg">{streak}</div>
          <div className="mt-1 text-xs text-fg-muted">day streak</div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1 text-[10px] text-fg-subtle" aria-hidden="true">
        Less
        {[0, 1, 2, 3].map((n) => (
          <span key={n} className="h-[9px] w-[9px] rounded-[2px]" style={{ background: level(n) }} />
        ))}
        More
      </div>
      {recent.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-line pt-3">
          {recent.slice(0, 3).map((entry) => (
            <li key={entry.id}>
              <Link to={`/handbook/entries/${entry.id}`} className="flex min-w-0 items-baseline gap-2 text-sm text-fg-soft hover:text-fg">
                <span className="w-14 shrink-0 text-xs tabular-nums text-fg-subtle">
                  {new Date(entry.entry_date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
                </span>
                <span className="truncate">{entry.project_title}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

// --- Reading -----------------------------------------------------------------------------

export function ReadingPanel({
  title = "Reading list",
  counts,
  items,
  canTrack,
  className = "",
}: { title?: string; counts: CountMap; items: ReadingListItem[]; canTrack: boolean } & Placement) {
  // Optimistic overrides from the toggles; the counts follow them.
  const [overrides, setOverrides] = useState<Record<string, ReadingStatus>>({});
  const live = { ...counts.counts };
  for (const item of items) {
    const next = overrides[item.paper_id];
    if (next && next !== item.status) {
      live[item.status] = (live[item.status] ?? 0) - 1;
      live[next] = (live[next] ?? 0) + 1;
    }
  }
  return (
    <Panel title={title} meta={counts.total || undefined} action={{ to: "/research", label: "Library" }} className={className} bodyClassName="">
      <div className="flex flex-wrap gap-x-5 gap-y-1 border-b border-line px-4 py-2.5 text-xs text-fg-muted">
        {READING_STATES.map((state) => (
          <span key={state.id} className="inline-flex items-center gap-1.5" data-testid={`reading-count-${state.id}`}>
            <span className="h-2 w-2 rounded-[2px]" style={{ background: READING_COLORS[state.id] }} aria-hidden="true" />
            {state.label}
            <span className="font-medium tabular-nums text-fg">{Math.max(0, live[state.id] ?? 0)}</span>
          </span>
        ))}
      </div>
      {items.length === 0 ? (
        <Empty>Papers linked to your projects appear here.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {items.slice(0, 6).map((item) => (
            <li key={item.paper_id} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5">
              <div className="min-w-0 flex-1 basis-52">
                <Link to={`/research/papers/${item.paper_id}`} className="block truncate text-sm font-medium text-fg hover:text-link">
                  {item.title}
                </Link>
                <div className="truncate text-xs text-fg-muted">{[item.venue, item.publication_year].filter(Boolean).join(" · ") || "—"}</div>
              </div>
              {canTrack && (
                <ReadingStatusToggle
                  compact
                  paperId={item.paper_id}
                  paperTitle={item.title}
                  status={item.status}
                  onChange={(next) => setOverrides((current) => ({ ...current, [item.paper_id]: next }))}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

// --- Projects ----------------------------------------------------------------------------

export function ProjectsPanel({
  title,
  projects,
  emptyText = "No projects yet.",
  showPipeline = false,
  showReviews = false,
  className = "",
}: { title: string; projects: ProjectSummaryItem[]; emptyText?: string; showPipeline?: boolean; showReviews?: boolean } & Placement) {
  return (
    <Panel title={title} meta={projects.length || undefined} action={{ to: "/projects", label: "All projects" }} className={className} bodyClassName="">
      {projects.length === 0 ? (
        <Empty>{emptyText}</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {projects.map((project) => {
            const ratio = project.assignments_total ? project.assignments_completed / project.assignments_total : 0;
            const repo = project.repo_links[0];
            // Only supervisors act on reviews (a student owner cannot review).
            const canReview = showReviews && (project.my_role === "owner" || project.my_role === "supervisor");
            return (
              <li
                key={project.id}
                className="relative grid grid-cols-1 items-center gap-x-6 gap-y-2 px-4 py-3 transition-colors duration-150 hover:bg-surface-muted sm:grid-cols-[minmax(0,1.4fr)_minmax(8rem,1fr)_auto]"
              >
                <div className="min-w-0">
                  <Link to={`/projects/${project.id}`} className="block truncate text-sm font-medium text-fg after:absolute after:inset-0 after:content-['']">
                    {project.title}
                  </Link>
                  <div className="flex flex-wrap items-center gap-x-2 text-xs text-fg-muted">
                    <span>{humanize(project.my_role ?? "member")}</span>
                    {project.status !== "active" && <span>· {humanize(project.status)}</span>}
                    {project.overdue > 0 && <span className="font-medium text-danger-fg">· {project.overdue} overdue</span>}
                    {canReview && project.pending_reviews > 0 && <span className="font-medium text-warn-fg">· {project.pending_reviews} to review</span>}
                  </div>
                </div>
                <div className="min-w-0">
                  {showPipeline ? (
                    <StackedBar
                      label={`${project.title} tasks`}
                      legend={false}
                      className="h-1.5"
                      segments={STAGES.map((s) => ({ key: s.key, label: s.label, color: s.color, value: project.assignment_counts[s.key] ?? 0 }))}
                    />
                  ) : (
                    <Progress ratio={ratio} />
                  )}
                  <div className="mt-1 text-xs tabular-nums text-fg-subtle">
                    {project.assignments_completed}/{project.assignments_total} tasks approved
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <AvatarStack members={project.members} total={project.member_count} />
                  {repo && (
                    <a
                      href={repo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={repo.label ?? repo.url}
                      className="relative z-10 inline-flex max-w-44 items-center gap-1.5 rounded-md border border-line px-2 py-1 text-xs text-fg-soft transition-colors duration-150 hover:border-line-strong hover:text-fg"
                    >
                      <GithubMark className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{repoName(repo.url)}</span>
                    </a>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

// --- Professor -------------------------------------------------------------------------

export function ReviewsPanel({ items, total, className = "" }: { items: ReviewItem[]; total: number } & Placement) {
  const now = new Date();
  return (
    <Panel title="Waiting for your review" meta={total || undefined} action={{ to: "/tasks?view=reviews", label: "Review queue" }} className={className} bodyClassName="">
      {items.length === 0 ? (
        <Empty>Nothing waiting for review.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => {
            const age = item.submitted_at ? daysSince(item.submitted_at, now) : 0;
            const tone: Tone = age >= 5 ? "danger" : age >= 3 ? "warn" : "neutral";
            return (
              <li key={item.assignment_id}>
                <Link
                  to={`/tasks/${item.task_id}?assignment=${item.assignment_id}`}
                  className="flex min-w-0 items-center gap-3 px-4 py-2.5 transition-colors duration-150 hover:bg-surface-muted"
                >
                  <Avatar name={item.student_username} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-fg">{item.task_title}</span>
                    <span className="block truncate text-xs text-fg-muted">
                      @{item.student_username} · {item.project_title}
                    </span>
                  </span>
                  <span
                    className={`flex items-center gap-1.5 text-xs whitespace-nowrap tabular-nums ${TONE_TEXT[tone]}`}
                    title={item.submitted_at ? `Submitted ${formatDateTime(item.submitted_at)}` : undefined}
                  >
                    {tone !== "neutral" && <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]}`} aria-hidden="true" />}
                    {age === 0 ? "today" : `${age}d waiting`}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

export function MemberReadingPanel({ rows, className = "" }: { rows: MemberReading[] } & Placement) {
  return (
    <Panel title="Member reading" action={{ to: "/research", label: "Library" }} className={className} bodyClassName="">
      {rows.length === 0 ? (
        <Empty>No member reading yet.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((row) => (
            <li key={row.user_id} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5">
              <Avatar name={row.full_name} title={`${row.full_name} (@${row.username})`} />
              <div className="min-w-0">
                <div className="truncate text-sm text-fg">{row.full_name}</div>
                <div className="mt-1.5">
                  <StackedBar
                    label={`${row.full_name} reading`}
                    legend={false}
                    className="h-1.5"
                    segments={READING_STATES.map((s) => ({ key: s.id, label: s.label, value: row.counts[s.id] ?? 0, color: READING_COLORS[s.id] }))}
                  />
                </div>
              </div>
              <span className="text-xs tabular-nums text-fg-muted" title="Completed of total">
                <span className="font-medium text-fg">{row.counts.completed ?? 0}</span>/{row.total}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function FeedRow({ who, children, when, to }: { who: string; children: ReactNode; when: string; to?: string }) {
  const body = (
    <>
      <Avatar name={who} />
      <span className="min-w-0 flex-1 text-sm text-fg-soft">
        <span className="font-medium text-fg">{who}</span> {children}
      </span>
      <span className="shrink-0 text-xs whitespace-nowrap tabular-nums text-fg-subtle">{when}</span>
    </>
  );
  const cls = "flex min-w-0 items-start gap-3 px-4 py-2.5";
  return to ? (
    <Link to={to} className={`${cls} transition-colors duration-150 hover:bg-surface-muted`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

function ago(iso: string): string {
  const days = daysSince(iso);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

export function HandbookFeedPanel({ items, className = "" }: { items: HandbookItem[] } & Placement) {
  return (
    <Panel title="Handbook activity" action={{ to: "/handbook", label: "Handbook" }} className={className} bodyClassName="">
      {items.length === 0 ? (
        <Empty>No handbook entries yet.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {items.slice(0, 6).map((entry) => (
            <li key={entry.id}>
              <FeedRow who={entry.student_username} when={ago(entry.entry_date)} to={`/handbook/entries/${entry.id}`}>
                wrote an entry in <span className="text-fg">{entry.project_title}</span>
                {entry.comment_count > 0 && <span className="text-fg-subtle"> · {entry.comment_count} comments</span>}
              </FeedRow>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

// --- Administrator ------------------------------------------------------------------

export function AuditPanel({ items, className = "" }: { items: ActivityItem[] } & Placement) {
  return (
    <Panel title="Recent activity" action={{ to: "/admin/audit", label: "Audit log" }} className={className} bodyClassName="">
      {items.length === 0 ? (
        <Empty>No activity recorded yet.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {items.slice(0, 8).map((item) => (
            <li key={item.id}>
              <FeedRow who={item.actor_username ?? "system"} when={ago(item.created_at)}>
                {humanize(item.action.replace(/\./g, " ")).toLowerCase()}
                <span className="text-fg-subtle"> · {humanize(item.entity_type).toLowerCase()}</span>
              </FeedRow>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export function AccountsPanel({ users, projects, className = "" }: { users: CountMap; projects: CountMap } & Placement) {
  return (
    <Panel title="Accounts and projects" action={{ to: "/admin/users", label: "Users" }} className={className}>
      <div className="space-y-5">
        <div>
          <div className="mb-2 text-xs text-fg-muted">
            <span className="font-medium tabular-nums text-fg">{users.total}</span> accounts
          </div>
          <StackedBar
            label="Accounts by status"
            segments={[
              { key: "approved", label: "Active", value: users.counts.approved ?? 0, color: "var(--primary)", to: "/admin/users" },
              { key: "pending", label: "Pending", value: users.counts.pending ?? 0, color: "var(--warn)", to: "/admin/users" },
              { key: "suspended", label: "Suspended", value: users.counts.suspended ?? 0, color: "var(--line-strong)", to: "/admin/users" },
              { key: "rejected", label: "Rejected", value: users.counts.rejected ?? 0, color: "var(--danger)", to: "/admin/users" },
            ]}
          />
        </div>
        <div>
          <div className="mb-2 text-xs text-fg-muted">
            <span className="font-medium tabular-nums text-fg">{projects.total}</span> projects
          </div>
          <StackedBar
            label="Projects by status"
            segments={[
              { key: "active", label: "Active", value: projects.counts.active ?? 0, color: "var(--primary)", to: "/projects?status=active" },
              { key: "archived", label: "Archived", value: projects.counts.archived ?? 0, color: "var(--line-strong)", to: "/projects?status=archived" },
              { key: "deleted", label: "In recovery", value: projects.counts.deleted ?? 0, color: "var(--danger)", to: "/projects?status=deleted" },
            ]}
          />
        </div>
      </div>
    </Panel>
  );
}

export function QueuePanel({ notifications, className = "" }: { notifications: CountMap } & Placement) {
  const c = notifications.counts;
  const waiting = (c.pending ?? 0) + (c.processing ?? 0) + (c.retry_scheduled ?? 0);
  const settled = (c.sent ?? 0) + (c.failed ?? 0);
  const rate = settled ? (c.sent ?? 0) / settled : 1;
  const tone: Tone = rate >= 0.95 ? "success" : rate >= 0.8 ? "warn" : "danger";
  return (
    <Panel title="Discord delivery" className={className}>
      <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
        <div>
          <div className="text-2xl leading-none font-semibold tracking-[-0.02em] tabular-nums text-fg">{Math.round(rate * 100)}%</div>
          <div className={`mt-1 flex items-center gap-1.5 text-xs ${TONE_TEXT[tone]}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]}`} aria-hidden="true" />
            delivered
          </div>
        </div>
        <div>
          <div className="text-2xl leading-none font-semibold tracking-[-0.02em] tabular-nums text-fg">{waiting}</div>
          <div className="mt-1 text-xs text-fg-muted">waiting</div>
        </div>
        {(c.failed ?? 0) > 0 && (
          <div>
            <div className="text-2xl leading-none font-semibold tracking-[-0.02em] tabular-nums text-danger-fg">{c.failed}</div>
            <div className="mt-1 text-xs text-fg-muted">failed</div>
          </div>
        )}
      </div>
      <div className="mt-4">
        <StackedBar
          label="Notifications by status"
          segments={[
            { key: "sent", label: "Sent", value: c.sent ?? 0, color: "var(--primary)" },
            { key: "pending", label: "Pending", value: (c.pending ?? 0) + (c.processing ?? 0), color: accentMix(40) },
            { key: "retry_scheduled", label: "Retrying", value: c.retry_scheduled ?? 0, color: "var(--warn)" },
            { key: "failed", label: "Failed", value: c.failed ?? 0, color: "var(--danger)" },
          ]}
        />
      </div>
    </Panel>
  );
}

export function LibraryPanel({ count, className = "" }: { count: number } & Placement) {
  return (
    <Panel title="Shared literature" className={className}>
      <div className="text-[28px] leading-none font-semibold tracking-[-0.02em] tabular-nums text-fg">{count}</div>
      <p className="mt-1.5 text-sm text-fg-muted">papers linked to the projects shared with you</p>
    </Panel>
  );
}
