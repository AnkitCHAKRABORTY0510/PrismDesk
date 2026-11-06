import { Link } from "react-router";

import { countdown, formatDate, formatDateTime, humanize, percent } from "../../lib/format";
import type {
  ActivityItem,
  CountMap,
  DeadlineItem,
  HandbookItem,
  ProjectSummaryItem,
} from "../../services/dashboardService";
import { Badge, Card, DataTable, EmptyState, ProgressBar, StatusBadge } from "../../components/ui";

export function CountBreakdown({ title, data }: { title: string; data: CountMap }) {
  return (
    <Card title={title}>
      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        {Object.entries(data.counts).map(([key, value]) => (
          <div key={key} className="rounded-lg bg-slate-50 px-3 py-2">
            <dt className="text-xs text-slate-500">{humanize(key)}</dt>
            <dd className="text-lg font-semibold text-slate-800">{value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

export function DeadlineList({ title, items }: { title: string; items: DeadlineItem[] }) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <EmptyState title="No upcoming deadlines" />
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`} className="flex items-center justify-between gap-3 py-2 text-sm">
              <div>
                <Link
                  to={item.kind === "task" ? `/tasks/${item.id}` : `/conferences?highlight=${item.id}`}
                  className="font-medium text-slate-800 hover:text-brand"
                >
                  {item.title}
                </Link>
                <div className="text-xs text-slate-500">
                  {item.kind === "task" ? "Task" : "Conference"}
                  {item.project_title ? ` · ${item.project_title}` : ""} · {formatDateTime(item.due_at)}
                </div>
              </div>
              <Badge tone="amber">{countdown(item.due_at)}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ProjectTable({ title, projects }: { title: string; projects: ProjectSummaryItem[] }) {
  return (
    <Card title={title}>
      <DataTable
        rows={projects}
        rowKey={(row) => row.id}
        empty="No projects yet."
        columns={[
          {
            header: "Project",
            cell: (row) => (
              <Link to={`/projects/${row.id}`} className="font-medium text-slate-800 hover:text-brand">
                {row.title}
              </Link>
            ),
          },
          { header: "Status", cell: (row) => <StatusBadge status={row.status} /> },
          { header: "Role", cell: (row) => humanize(row.my_role ?? "—") },
          { header: "Members", cell: (row) => row.member_count },
          {
            header: "Task completion",
            cell: (row) =>
              row.assignments_total ? (
                <div className="w-32">
                  <ProgressBar
                    value={row.assignments_completed / row.assignments_total}
                    label={`${row.assignments_completed}/${row.assignments_total}`}
                  />
                </div>
              ) : (
                "—"
              ),
          },
          { header: "Reviews", cell: (row) => row.pending_reviews },
          { header: "Overdue", cell: (row) => (row.overdue ? <Badge tone="red">{row.overdue}</Badge> : 0) },
        ]}
      />
    </Card>
  );
}

export function HandbookList({ title, items }: { title: string; items: HandbookItem[] }) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <EmptyState title="No handbook entries yet" />
      ) : (
        <ul className="divide-y divide-slate-100 text-sm">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between py-2">
              <div>
                <Link to={`/handbook/entries/${item.id}`} className="font-medium text-slate-800 hover:text-brand">
                  {formatDate(item.entry_date)} · {item.project_title}
                </Link>
                <div className="text-xs text-slate-500">@{item.student_username}</div>
              </div>
              <span className="text-xs text-slate-500">{item.comment_count} comments</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ActivityList({ items }: { items: ActivityItem[] }) {
  return (
    <Card title="Recent administrative activity" actions={<Link to="/admin/audit" className="text-sm text-brand">View audit log</Link>}>
      {items.length === 0 ? (
        <EmptyState title="No activity recorded yet" />
      ) : (
        <ul className="divide-y divide-slate-100 text-sm">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between py-2">
              <span>
                <strong className="font-medium">{item.actor_username ?? "system"}</strong> · {humanize(item.action)}
              </span>
              <span className="text-xs text-slate-500">{formatDateTime(item.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ReadingProgress({ data }: { data: CountMap }) {
  const completed = data.counts.completed ?? 0;
  return (
    <Card title="Reading progress">
      {data.total === 0 ? (
        <EmptyState title="No papers tracked yet" />
      ) : (
        <div className="space-y-3">
          <ProgressBar value={completed / data.total} label={`${completed} of ${data.total} completed`} />
          <div className="flex gap-4 text-xs text-slate-500">
            <span>Reading: {data.counts.reading ?? 0}</span>
            <span>Not started: {data.counts.not_started ?? 0}</span>
            <span>Completion: {percent(completed / data.total)}</span>
          </div>
        </div>
      )}
    </Card>
  );
}
