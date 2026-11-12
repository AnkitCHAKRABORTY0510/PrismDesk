import { useState } from "react";
import { Link } from "react-router";

import {
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  ErrorMessage,
  Loading,
  Pagination,
  ProgressBar,
  SearchInput,
  Select,
  StatCard,
  StatusBadge,
  UserPicker,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { formatDate, formatDateTime, humanize, percent } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import { listConferences } from "../../services/conferenceService";
import { projectAnalytics } from "../../services/dashboardService";
import { listEntries } from "../../services/handbookService";
import {
  addMember,
  changeMemberRole,
  listMembers,
  removeMember,
  transferOwnership,
  type MembershipRole,
  type Project,
  type ProjectMember,
} from "../../services/projectService";
import { ReadingStatusToggle } from "../../components/research/ReadingStatusToggle";
import { linkPaper, listPapers, projectReadingProgress, unlinkPaper } from "../../services/researchService";
import type { UserSummary } from "../../services/types";
import { listTasks } from "../../services/taskService";
import ConferenceFormModal from "../conferences/ConferenceFormModal";
import { ConferenceCards } from "../conferences/ConferenceList";
import EntryFormModal from "../handbook/EntryFormModal";
import PaperFormModal from "../research/PaperFormModal";
import TaskFormModal from "../tasks/TaskFormModal";

type AssignableRole = Exclude<MembershipRole, "owner">;

function rolesFor(user: UserSummary): AssignableRole[] {
  if (user.roles.length === 1 && user.roles[0] === "Guest") return ["guest"];
  return user.roles.includes("Professor") ? ["supervisor", "member"] : ["member"];
}

export function MembersTab({ project, onChanged }: { project: Project; onChanged: () => Promise<void> }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const manage = project.permissions.can_manage_members;
  const [showRemoved, setShowRemoved] = useState(false);
  const members = useAsync(() => listMembers(project.id, showRemoved), [project.id, showRemoved]);
  const [pending, setPending] = useState<UserSummary | null>(null);
  const [role, setRole] = useState<AssignableRole>("member");
  const [removing, setRemoving] = useState<ProjectMember | null>(null);

  const act = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      notify(message);
      await members.reload();
      await onChanged();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  const activeIds = (members.data ?? []).filter((m) => m.membership_status === "active").map((m) => m.user.id);

  return (
    <div className="space-y-6">
      {manage && (
        <Card title="Add member">
          {pending ? (
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span>
                <strong>{pending.full_name}</strong> as
              </span>
              <Select aria-label="Membership role" className="w-auto" value={role} onChange={(e) => setRole(e.target.value as AssignableRole)}>
                {rolesFor(pending).map((r) => (
                  <option key={r} value={r}>{humanize(r)}</option>
                ))}
              </Select>
              <Button size="sm" onClick={() => void act(() => addMember(project.id, pending.id, role), `${pending.full_name} added.`).then(() => setPending(null))}>
                Add
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setPending(null)}>Cancel</Button>
            </div>
          ) : (
            <UserPicker
              excludeIds={activeIds}
              onSelect={(picked) => {
                setPending(picked);
                setRole(rolesFor(picked)[0]);
              }}
            />
          )}
          <p className="mt-2 text-xs text-fg-muted">Guests receive read-only access to this project only.</p>
        </Card>
      )}
      <Card
        title="Members"
        actions={
          manage && (
            <label className="flex items-center gap-2 text-sm text-fg-soft">
              <input type="checkbox" checked={showRemoved} onChange={(e) => setShowRemoved(e.target.checked)} /> Show removed
            </label>
          )
        }
      >
        <ErrorMessage message={members.error} onRetry={members.reload} />
        {members.loading && !members.data ? (
          <Loading />
        ) : (
          <DataTable
            rows={members.data ?? []}
            rowKey={(row) => row.id}
            columns={[
              { header: "Member", cell: (row) => <div><div className="font-medium">{row.user.full_name}</div><div className="text-xs text-fg-muted">@{row.user.username}</div></div> },
              { header: "Global roles", cell: (row) => row.user.roles.join(", ") },
              {
                header: "Project role",
                cell: (row) =>
                  manage && row.membership_role !== "owner" && row.membership_status === "active" ? (
                    <Select
                      aria-label={`Project role for ${row.user.username}`}
                      className="w-auto"
                      value={row.membership_role}
                      onChange={(e) => void act(() => changeMemberRole(project.id, row.user.id, e.target.value as AssignableRole), "Role updated.")}
                    >
                      {rolesFor(row.user).map((r) => <option key={r} value={r}>{humanize(r)}</option>)}
                    </Select>
                  ) : (
                    humanize(row.membership_role)
                  ),
              },
              { header: "Status", cell: (row) => <StatusBadge status={row.membership_status === "active" ? "active" : "archived"} /> },
              { header: "Joined", cell: (row) => formatDate(row.joined_at) },
              {
                header: "",
                cell: (row) => (
                  <div className="flex gap-2">
                    {manage && row.membership_role !== "owner" && row.membership_status === "active" && (
                      <Button size="sm" variant="ghost" onClick={() => setRemoving(row)}>Remove</Button>
                    )}
                    {can(user, "users.manage") && row.membership_role !== "owner" && row.membership_status === "active" && !row.user.roles.every((r) => r === "Guest") && (
                      <Button size="sm" variant="ghost" onClick={() => void act(() => transferOwnership(project.id, row.user.id), "Ownership transferred.")}>
                        Make owner
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Card>
      <ConfirmDialog
        open={removing !== null}
        title="Remove member"
        message={`Remove ${removing?.user.full_name} from this project? Their past work stays in the project history.`}
        confirmLabel="Remove"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={() => removing && void act(() => removeMember(project.id, removing.user.id), "Member removed.").then(() => setRemoving(null))}
      />
    </div>
  );
}

export function PapersTab({ project }: { project: Project }) {
  const { notify } = useToast();
  const contribute = project.permissions.can_contribute;
  const { user } = useAuth();
  const tracks = can(user, "research.track_progress");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(false);
  const [linkSearch, setLinkSearch] = useState("");
  const q = useDebounced(linkSearch);
  const papers = useAsync(() => listPapers({ project_id: project.id, page, page_size: 20 }), [project.id, page]);
  const candidates = useAsync(
    () => (q.trim().length >= 2 ? listPapers({ search: q, page_size: 8 }) : Promise.resolve(null)),
    [q]
  );
  const progress = useAsync(
    () => (project.permissions.can_review ? projectReadingProgress(project.id) : Promise.resolve([])),
    [project.id]
  );

  const act = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      notify(message);
      await papers.reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  const linkedIds = (papers.data?.items ?? []).map((p) => p.id);

  return (
    <div className="space-y-6">
      {contribute && (
        <Card title="Add literature" actions={<Button size="sm" onClick={() => setAdding(true)}>New paper</Button>}>
          <SearchInput label="Find existing paper" value={linkSearch} onChange={setLinkSearch} placeholder="Search the lab library to link an existing paper…" />
          {candidates.data && (
            <ul className="mt-2 divide-y divide-line rounded-lg border border-line">
              {candidates.data.items.filter((p) => !linkedIds.includes(p.id)).map((paper) => (
                <li key={paper.id} className="flex items-center justify-between px-3 py-2 text-sm">
                  <span>{paper.title} <span className="text-xs text-fg-muted">{paper.publication_year}</span></span>
                  <Button size="sm" variant="secondary" onClick={() => void act(() => linkPaper(paper.id, project.id), "Paper linked.").then(() => setLinkSearch(""))}>
                    Link
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
      <Card title="Project literature">
        <ErrorMessage message={papers.error} onRetry={papers.reload} />
        {papers.loading && !papers.data ? (
          <Loading />
        ) : (
          papers.data && (
            <>
              <DataTable
                rows={papers.data.items}
                rowKey={(row) => row.id}
                empty="No papers linked to this project yet."
                columns={[
                  { header: "Title", cell: (row) => <Link className="font-medium hover:text-link" to={`/research/papers/${row.id}`}>{row.title}</Link> },
                  { header: "Authors", cell: (row) => <span className="text-xs">{row.authors.join(", ")}</span> },
                  { header: "Year", cell: (row) => row.publication_year ?? "—" },
                  {
                    header: "My status",
                    cell: (row) =>
                      tracks ? (
                        <ReadingStatusToggle
                          compact
                          paperId={row.id}
                          paperTitle={row.title}
                          status={row.my_status}
                          onChange={(next) => {
                            const current = papers.data;
                            if (current)
                              papers.setData({ ...current, items: current.items.map((p) => (p.id === row.id ? { ...p, my_status: next } : p)) });
                          }}
                        />
                      ) : (
                        <StatusBadge status={row.my_status ?? "not_started"} />
                      ),
                  },
                  {
                    header: "",
                    cell: (row) =>
                      contribute && (
                        <Button size="sm" variant="ghost" onClick={() => void act(() => unlinkPaper(row.id, project.id), "Paper removed from project.")}>
                          Remove
                        </Button>
                      ),
                  },
                ]}
              />
              <Pagination page={page} pageSize={20} total={papers.data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>
      {project.permissions.can_review && (progress.data ?? []).length > 0 && (
        <Card title="Member reading progress">
          <DataTable
            rows={progress.data ?? []}
            rowKey={(row) => `${row.user_id}-${row.paper_id}-${row.project_id}`}
            columns={[
              { header: "Student", cell: (row) => row.username },
              { header: "Paper", cell: (row) => row.paper_title },
              { header: "Status", cell: (row) => <StatusBadge status={row.status} /> },
              { header: "Updated", cell: (row) => formatDateTime(row.updated_at) },
            ]}
          />
        </Card>
      )}
      {adding && (
        <PaperFormModal
          open
          projectId={project.id}
          onClose={() => setAdding(false)}
          onSaved={(paper) => {
            setAdding(false);
            notify(paper.linked_existing ? "This paper already existed; it was linked instead of duplicated." : "Paper added.");
            void papers.reload();
          }}
        />
      )}
    </div>
  );
}

export function TasksTab({ project }: { project: Project }) {
  const { notify } = useToast();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const members = useAsync(() => (project.permissions.can_review ? listMembers(project.id) : Promise.resolve([])), [project.id]);
  const tasks = useAsync(
    () => listTasks({ project_id: project.id, scope: "all", task_type: "official", status, page, page_size: 20 }),
    [project.id, status, page]
  );

  return (
    <Card
      title="Official tasks"
      actions={
        <>
          <Select aria-label="Status" className="w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="">All statuses</option>
            {["todo", "in_progress", "under_review", "revision_required", "completed"].map((s) => (
              <option key={s} value={s}>{humanize(s)}</option>
            ))}
          </Select>
          {project.permissions.can_review && <Button onClick={() => setCreating(true)}>New task</Button>}
        </>
      }
    >
      <ErrorMessage message={tasks.error} onRetry={tasks.reload} />
      {tasks.loading && !tasks.data ? (
        <Loading />
      ) : (
        tasks.data && (
          <>
            <DataTable
              rows={tasks.data.items}
              rowKey={(row) => row.id}
              empty="No tasks visible to you in this project."
              columns={[
                { header: "Task", cell: (row) => <Link className="font-medium hover:text-link" to={`/tasks/${row.id}`}>{row.title}</Link> },
                { header: "Priority", cell: (row) => <StatusBadge status={row.priority} /> },
                { header: "Due", cell: (row) => formatDateTime(row.due_at) },
                {
                  header: "Progress",
                  cell: (row) =>
                    row.my_assignment ? (
                      <StatusBadge status={row.my_assignment.status} />
                    ) : (
                      `${row.assignments.filter((a) => a.status === "completed").length}/${row.assignments.length} completed`
                    ),
                },
              ]}
            />
            <Pagination page={page} pageSize={20} total={tasks.data.total} onChange={setPage} />
          </>
        )
      )}
      {creating && (
        <TaskFormModal
          open
          taskType="official"
          projectId={project.id}
          members={members.data ?? []}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            notify("Task created.");
            void tasks.reload();
          }}
        />
      )}
    </Card>
  );
}

export function HandbookTab({ project }: { project: Project }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const entries = useAsync(() => listEntries({ project_id: project.id, page, page_size: 20 }), [project.id, page]);
  const canWrite = can(user, "handbook.write") && project.permissions.can_contribute && (project.my_role === "owner" || project.my_role === "member");

  return (
    <Card title="Project-wise daily entries" actions={canWrite && <Button onClick={() => setCreating(true)}>New entry</Button>}>
      <p className="mb-3 text-xs text-fg-muted">
        Students see their own entries; supervisors see every member's entries for this project.
      </p>
      <ErrorMessage message={entries.error} onRetry={entries.reload} />
      {entries.loading && !entries.data ? (
        <Loading />
      ) : (
        entries.data && (
          <>
            <DataTable
              rows={entries.data.items}
              rowKey={(row) => row.id}
              empty="No entries yet."
              columns={[
                { header: "Date", cell: (row) => <Link className="font-medium hover:text-link" to={`/handbook/entries/${row.id}`}>{formatDate(row.entry_date)}</Link> },
                { header: "Student", cell: (row) => row.student.full_name },
                { header: "Work completed", cell: (row) => <span className="line-clamp-2">{row.work_completed || "—"}</span> },
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
          projectId={project.id}
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

export function ConferencesTab({ project }: { project: Project }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const [showArchived, setShowArchived] = useState(false);
  const [adding, setAdding] = useState(false);
  const conferences = useAsync(
    () => listConferences({ project_id: project.id, include_archived_links: showArchived || undefined, page_size: 50 }),
    [project.id, showArchived]
  );

  return (
    <Card
      title="Conference deadlines"
      actions={
        <>
          <label className="flex items-center gap-2 text-sm text-fg-soft">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /> Include archived
          </label>
          {project.permissions.can_contribute && can(user, "conferences.create") && <Button onClick={() => setAdding(true)}>Add conference</Button>}
        </>
      }
    >
      <ErrorMessage message={conferences.error} onRetry={conferences.reload} />
      {conferences.loading && !conferences.data ? (
        <Loading />
      ) : (
        <ConferenceCards items={conferences.data?.items ?? []} projectId={project.id} onChanged={() => void conferences.reload()} />
      )}
      {adding && (
        <ConferenceFormModal
          open
          projectId={project.id}
          onClose={() => setAdding(false)}
          onSaved={(c) => {
            setAdding(false);
            notify(c.linked_existing ? "Existing conference linked to this project." : "Conference added.");
            void conferences.reload();
          }}
        />
      )}
    </Card>
  );
}

export function AnalyticsTab({ project }: { project: Project }) {
  const data = useAsync(() => projectAnalytics(project.id), [project.id]);
  if (data.loading && !data.data) return <Loading />;
  if (data.error) return <ErrorMessage message={data.error} onRetry={data.reload} />;
  if (!data.data) return null;
  const a = data.data;
  const maxWeek = Math.max(1, ...a.handbook_per_week.map((w) => w.count));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Task completion" value={percent(a.completion_rate)} hint={`${a.assignments.counts.completed}/${a.assignments.total} assignments`} />
        <StatCard label="Pending reviews" value={a.assignments.counts.under_review} />
        <StatCard label="Overdue assignments" value={a.overdue_assignments} />
        <StatCard label="Activity (30 days)" value={a.activity_last_30_days} hint="project audit events" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Reading progress">
          <ProgressBar
            value={a.reading_progress.total ? (a.reading_progress.counts.completed ?? 0) / a.reading_progress.total : 0}
            label={`${a.reading_progress.counts.completed ?? 0} completed · ${a.reading_progress.counts.reading ?? 0} reading · ${a.paper_count} papers`}
          />
        </Card>
        <Card title="Handbook entries per week (8 weeks)">
          {a.handbook_per_week.length === 0 ? (
            <p className="text-sm text-fg-muted">No entries in the last 8 weeks.</p>
          ) : (
            <ul className="space-y-2 text-xs">
              {a.handbook_per_week.map((w) => (
                <li key={w.week_start} className="flex items-center gap-3">
                  <span className="w-20 text-fg-muted">{formatDate(w.week_start)}</span>
                  <span className="h-3 rounded bg-brand" style={{ width: `${(w.count / maxWeek) * 70}%` }} />
                  <span>{w.count}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
