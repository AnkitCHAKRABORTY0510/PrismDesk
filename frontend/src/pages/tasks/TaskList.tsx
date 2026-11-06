import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  DataTable,
  ErrorMessage,
  FilterSelect,
  Loading,
  Pagination,
  SearchInput,
  StatusBadge,
  Tabs,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { formatDateTime, humanize } from "../../lib/format";
import { can } from "../../lib/permissions";
import { listTasks, pendingReviews } from "../../services/taskService";
import TaskFormModal from "./TaskFormModal";

type View = "mine" | "personal" | "managed" | "reviews";

const STATUSES = ["todo", "in_progress", "under_review", "revision_required", "completed"];

export default function TaskList() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [params, setParams] = useSearchParams();
  const canReview = can(user, "tasks.review");
  const view = (params.get("view") as View) || (canReview && !can(user, "tasks.personal") ? "managed" : "mine");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [overdue, setOverdue] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const q = useDebounced(search);

  const tabs: { id: View; label: string }[] = [
    ...(can(user, "tasks.personal") ? [{ id: "mine" as View, label: "My tasks" }, { id: "personal" as View, label: "Personal" }] : []),
    ...(canReview ? [{ id: "managed" as View, label: "Project tasks" }, { id: "reviews" as View, label: "Review queue" }] : []),
  ];

  const tasks = useAsync(
    () =>
      view === "reviews"
        ? Promise.resolve(null)
        : listTasks({ scope: view, status, priority, overdue: overdue || undefined, search: q, page, page_size: 20 }),
    [view, status, priority, overdue, q, page]
  );
  const reviews = useAsync(() => (view === "reviews" ? pendingReviews({ page, page_size: 20 }) : Promise.resolve(null)), [view, page]);

  const switchView = (next: View) => {
    setPage(1);
    setParams({ view: next });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tasks"
        description="Official project tasks follow To Do → In Progress → Under Review → Revision Required/Completed."
        actions={can(user, "tasks.personal") && <Button onClick={() => setCreating(true)}>New personal task</Button>}
      />
      {tabs.length > 1 && <Tabs tabs={tabs} active={view} onChange={switchView} />}

      {view === "reviews" ? (
        <Card title="Submissions awaiting your review">
          <ErrorMessage message={reviews.error} onRetry={reviews.reload} />
          {reviews.loading && !reviews.data ? (
            <Loading />
          ) : (
            reviews.data && (
              <>
                <DataTable
                  rows={reviews.data.items}
                  rowKey={(row) => row.assignment.id}
                  empty="Nothing waiting for review."
                  columns={[
                    { header: "Task", cell: (row) => <Link className="font-medium hover:text-brand" to={`/tasks/${row.task_id}?assignment=${row.assignment.id}`}>{row.task_title}</Link> },
                    { header: "Student", cell: (row) => row.assignment.assignee.full_name },
                    { header: "Project", cell: (row) => row.project_title },
                    { header: "Version", cell: (row) => `v${row.latest_version ?? "?"}` },
                    { header: "Submitted", cell: (row) => formatDateTime(row.submitted_at) },
                  ]}
                />
                <Pagination page={page} pageSize={20} total={reviews.data.total} onChange={setPage} />
              </>
            )
          )}
        </Card>
      ) : (
        <Card>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search task titles…" />
            <FilterSelect label="Status" value={status} allLabel="All statuses" onChange={(v) => { setStatus(v); setPage(1); }} options={STATUSES.map((s) => ({ value: s, label: humanize(s) }))} />
            <FilterSelect label="Priority" value={priority} allLabel="All priorities" onChange={(v) => { setPriority(v); setPage(1); }} options={["low", "medium", "high", "urgent"].map((p) => ({ value: p, label: humanize(p) }))} />
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={overdue} onChange={(e) => { setOverdue(e.target.checked); setPage(1); }} /> Overdue only
            </label>
          </div>
          <ErrorMessage message={tasks.error} onRetry={tasks.reload} />
          {tasks.loading && !tasks.data ? (
            <Loading />
          ) : (
            tasks.data && (
              <>
                <DataTable
                  rows={tasks.data.items}
                  rowKey={(row) => row.id}
                  empty="No tasks found."
                  columns={[
                    {
                      header: "Task",
                      cell: (row) => (
                        <div>
                          <Link to={`/tasks/${row.id}`} className="font-medium text-slate-800 hover:text-brand">{row.title}</Link>
                          <div className="text-xs text-slate-500">{row.task_type === "personal" ? "Personal" : row.project_title}</div>
                        </div>
                      ),
                    },
                    { header: "Priority", cell: (row) => <StatusBadge status={row.priority} /> },
                    {
                      header: "Due",
                      cell: (row) => (
                        <span className="flex items-center gap-2">
                          {formatDateTime(row.due_at)}
                          {row.is_overdue && <Badge tone="red">Overdue</Badge>}
                        </span>
                      ),
                    },
                    {
                      header: "Status",
                      cell: (row) =>
                        row.my_assignment ? (
                          <StatusBadge status={row.my_assignment.status} />
                        ) : (
                          <span className="text-xs text-slate-500">
                            {row.assignments.filter((a) => a.status === "completed").length}/{row.assignments.length} completed
                          </span>
                        ),
                    },
                  ]}
                />
                <Pagination page={page} pageSize={20} total={tasks.data.total} onChange={setPage} />
              </>
            )
          )}
        </Card>
      )}

      {creating && (
        <TaskFormModal
          open
          taskType="personal"
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            notify("Personal task created.");
            void tasks.reload();
          }}
        />
      )}
    </div>
  );
}
