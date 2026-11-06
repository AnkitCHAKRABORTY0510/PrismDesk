import { useState } from "react";
import { Link } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import { Card, ErrorMessage, Loading, StatCard, Tabs } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { percent } from "../../lib/format";
import { can } from "../../lib/permissions";
import {
  adminDashboard,
  guestDashboard,
  professorDashboard,
  studentDashboard,
} from "../../services/dashboardService";
import PendingRegistrations from "../admin/PendingRegistrations";
import {
  ActivityList,
  CountBreakdown,
  DeadlineList,
  HandbookList,
  ProjectTable,
  ReadingProgress,
} from "./widgets";

type View = "admin" | "professor" | "student" | "guest";

const VIEWS: { id: View; label: string; capability: string }[] = [
  { id: "admin", label: "Administrator", capability: "dashboard.admin" },
  { id: "professor", label: "Professor", capability: "dashboard.professor" },
  { id: "student", label: "Student", capability: "dashboard.student" },
  { id: "guest", label: "Guest", capability: "dashboard.guest" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const available = VIEWS.filter((view) => can(user, view.capability));
  const [view, setView] = useState<View>(available[0]?.id ?? "guest");

  return (
    <div className="space-y-6">
      <PageHeader title={`Welcome, ${user?.full_name ?? ""}`} description="One Lab. Multiple Projects. Connected Research." />
      {available.length > 1 && <Tabs tabs={available} active={view} onChange={setView} />}
      {view === "admin" && <AdminView />}
      {view === "professor" && <ProfessorView />}
      {view === "student" && <StudentView />}
      {view === "guest" && <GuestView />}
    </div>
  );
}

function AdminView() {
  const { data, loading, error, reload } = useAsync(adminDashboard, []);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total users" value={data.users.total} />
        <StatCard label="Pending registrations" value={data.users.counts.pending} />
        <StatCard label="Active users" value={data.users.counts.approved} />
        <StatCard label="Suspended users" value={data.users.counts.suspended} />
        <StatCard label="Total projects" value={data.projects.total} hint={`${data.projects.counts.deleted} in recovery`} />
        <StatCard label="Active projects" value={data.projects.counts.active} />
        <StatCard label="Archived projects" value={data.projects.counts.archived} />
        <StatCard label="Research papers" value={data.research_papers} />
      </div>

      <PendingRegistrations onChange={reload} />

      <div className="grid gap-6 lg:grid-cols-2">
        <CountBreakdown title={`Official task assignments (${data.overdue_assignments} overdue)`} data={data.tasks} />
        <CountBreakdown title="Discord notification queue" data={data.notifications} />
        <DeadlineList title="Upcoming conferences" items={data.upcoming_conferences} />
        <ActivityList items={data.recent_activity} />
      </div>

      <Card title="Administration">
        <div className="flex flex-wrap gap-3 text-sm">
          {[
            ["/admin/users", "User management"],
            ["/projects", "Project management"],
            ["/research", "Research management"],
            ["/tasks", "Task management"],
            ["/handbook", "Handbook"],
            ["/conferences", "Conference tracker"],
            ["/admin/audit", "Audit logs"],
            ["/admin/settings", "System settings"],
          ].map(([to, label]) => (
            <Link key={to} to={to} className="rounded-lg border border-slate-200 px-3 py-2 hover:border-brand hover:text-brand">
              {label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ProfessorView() {
  const { data, loading, error, reload } = useAsync(professorDashboard, []);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Supervised projects" value={data.supervised_projects.length} />
        <StatCard label="Project members" value={data.member_count} />
        <StatCard label="Pending reviews" value={data.pending_reviews} />
        <StatCard label="Papers read (members)" value={data.reading_progress.counts.completed} />
      </div>
      <ProjectTable title="Supervised projects" projects={data.supervised_projects} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Submissions awaiting review" actions={<Link to="/tasks?view=reviews" className="text-sm text-brand">Open review queue</Link>}>
          {data.review_queue.length === 0 ? (
            <p className="text-sm text-slate-500">Nothing to review.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {data.review_queue.map((item) => (
                <li key={item.assignment_id} className="py-2">
                  <Link to={`/tasks/${item.task_id}`} className="font-medium hover:text-brand">
                    {item.task_title}
                  </Link>
                  <div className="text-xs text-slate-500">
                    @{item.student_username} · {item.project_title}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <DeadlineList title="Upcoming deadlines" items={data.upcoming_deadlines} />
        <HandbookList title="Recent handbook entries" items={data.recent_handbook_entries} />
        <ReadingProgress data={data.reading_progress} />
      </div>
    </div>
  );
}

function StudentView() {
  const { data, loading, error, reload } = useAsync(studentDashboard, []);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Joined projects" value={data.joined_projects.length} hint={`${data.owned_project_count} owned`} />
        <StatCard label="Pending submissions" value={data.pending_submissions} />
        <StatCard label="Task completion" value={percent(data.task_completion_rate)} />
        <StatCard
          label="Handbook entries"
          value={data.handbook_entries_last_7_days}
          hint={`last 7 days · ${data.handbook_entries_last_30_days} in 30 days`}
        />
      </div>
      <ProjectTable title="My projects" projects={data.joined_projects} />
      <div className="grid gap-6 lg:grid-cols-2">
        <CountBreakdown title="Assigned tasks" data={data.assigned_tasks} />
        <CountBreakdown title="Personal tasks" data={data.personal_tasks} />
        <DeadlineList title="Upcoming deadlines" items={data.upcoming_deadlines} />
        <ReadingProgress data={data.reading_progress} />
        <HandbookList title="My recent handbook entries" items={data.recent_handbook_entries} />
      </div>
    </div>
  );
}

function GuestView() {
  const { data, loading, error, reload } = useAsync(guestDashboard, []);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <StatCard label="Projects shared with you" value={data.projects.length} />
        <StatCard label="Research papers" value={data.paper_count} />
        <StatCard label="Upcoming conferences" value={data.upcoming_conferences.length} />
      </div>
      <ProjectTable title="Read-only project access" projects={data.projects} />
      <DeadlineList title="Conference deadlines" items={data.upcoming_conferences} />
    </div>
  );
}
