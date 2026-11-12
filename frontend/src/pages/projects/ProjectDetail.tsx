import { useState, type ReactNode } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Alert,
  Button,
  Card,
  ConfirmDialog,
  ErrorMessage,
  Field,
  Loading,
  Modal,
  StatusBadge,
  Tabs,
  Textarea,
  useToast,
} from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDate, formatDateTime, humanize } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import {
  archiveProject,
  deleteProject,
  getProject,
  purgeProject,
  requestArchive,
  restoreProject,
  unarchiveProject,
  type Project,
} from "../../services/projectService";
import ProjectFormModal from "./ProjectFormModal";
import RepoLinksCard from "./RepoLinksCard";
import {
  AnalyticsTab,
  ConferencesTab,
  HandbookTab,
  MembersTab,
  PapersTab,
  TasksTab,
} from "./ProjectTabs";

type TabId = "overview" | "members" | "papers" | "tasks" | "handbook" | "conferences" | "analytics";

export default function ProjectDetail() {
  const { projectId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const project = useAsync(() => getProject(projectId), [projectId]);

  if (project.loading && !project.data) return <Loading />;
  if (project.error) return <ErrorMessage message={project.error} onRetry={project.reload} />;
  if (!project.data) return null;
  const p = project.data;

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "members", label: "Members" },
    { id: "papers", label: "Literature" },
    ...(p.my_role !== "guest" ? [{ id: "tasks" as TabId, label: "Tasks" }, { id: "handbook" as TabId, label: "Handbook" }] : []),
    { id: "conferences", label: "Conferences" },
    ...(p.permissions.can_review || (p.status !== "active" && p.permissions.can_unarchive)
      ? [{ id: "analytics" as TabId, label: "Analytics" }]
      : []),
  ];
  const active = (tabs.find((t) => t.id === params.get("tab"))?.id ?? "overview") as TabId;

  const content: Record<TabId, ReactNode> = {
    overview: <Overview project={p} onChanged={(next) => project.setData(next)} />,
    members: <MembersTab project={p} onChanged={project.reload} />,
    papers: <PapersTab project={p} />,
    tasks: <TasksTab project={p} />,
    handbook: <HandbookTab project={p} />,
    conferences: <ConferencesTab project={p} />,
    analytics: <AnalyticsTab project={p} />,
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={p.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={p.status} /> Owner {p.owner.full_name}
            {p.my_role && <> · your role: {humanize(p.my_role)}</>}
          </span>
        }
      />
      {p.status === "archived" && <Alert kind="info">This project is archived and read-only for ordinary activity.</Alert>}
      {p.status === "deleted" && (
        <Alert>
          This project is deleted. It can be restored until {formatDate(p.purge_eligible_at)}, after which an administrator
          may delete it permanently.
        </Alert>
      )}
      <Tabs tabs={tabs} active={active} onChange={(tab) => setParams({ tab })} />
      {content[active]}
    </div>
  );
}

function Overview({ project, onChanged }: { project: Project; onChanged: (project: Project) => void }) {
  const { notify } = useToast();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState<null | "archive" | "unarchive" | "delete" | "restore" | "purge">(null);
  const [busy, setBusy] = useState(false);
  const perms = project.permissions;

  const run = async () => {
    if (!confirm) return;
    setBusy(true);
    try {
      if (confirm === "purge") {
        await purgeProject(project.id);
        notify("Project permanently deleted.");
        navigate("/projects");
        return;
      }
      const actions = { archive: archiveProject, unarchive: unarchiveProject, delete: deleteProject, restore: restoreProject };
      onChanged(await actions[confirm](project.id));
      notify(`Project ${confirm === "delete" ? "deleted" : confirm + "d"}.`);
      setConfirm(null);
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const confirmText: Record<string, string> = {
    archive: "Archive this project? It becomes read-only until it is restored.",
    unarchive: "Restore this archived project to active?",
    delete: "Delete this project? It stays recoverable by administrators for 90 days.",
    restore: "Restore this deleted project?",
    purge: "Permanently delete this project and its tasks, handbook entries and associations? Shared papers and conferences are kept. This cannot be undone.",
  };

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card title="About" className="lg:col-span-2" actions={perms.can_edit && <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Edit</Button>}>
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium text-fg-soft">Description</h3>
            <p className="mt-1 whitespace-pre-line text-fg-soft">{project.description || "—"}</p>
          </div>
          <div>
            <h3 className="font-medium text-fg-soft">Research objectives</h3>
            <p className="mt-1 whitespace-pre-line text-fg-soft">{project.objectives || "—"}</p>
          </div>
        </div>
      </Card>
      <div className="space-y-6">
        <RepoLinksCard project={project} />
        <Card title="Details">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-fg-muted">Created</dt><dd>{formatDateTime(project.created_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-fg-muted">Last updated</dt><dd>{formatDateTime(project.updated_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-fg-muted">Members</dt><dd>{project.member_count}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-fg-muted">Supervisors</dt><dd className="text-right">{project.supervisors.map((s) => s.full_name).join(", ") || "—"}</dd></div>
          </dl>
          {project.archive_requested_at && project.status === "active" && (
            <div className="mt-4"><Alert kind="info">Archival requested on {formatDate(project.archive_requested_at)}{project.archive_request_reason ? `: ${project.archive_request_reason}` : "."}</Alert></div>
          )}
        </Card>
        <Card title="Lifecycle">
          <div className="flex flex-wrap gap-2">
            {perms.can_request_archive && <Button size="sm" variant="secondary" onClick={() => setRequesting(true)}>Request archival</Button>}
            {perms.can_archive && <Button size="sm" variant="secondary" onClick={() => setConfirm("archive")}>Archive</Button>}
            {perms.can_unarchive && <Button size="sm" variant="secondary" onClick={() => setConfirm("unarchive")}>Restore from archive</Button>}
            {perms.can_delete && <Button size="sm" variant="danger" onClick={() => setConfirm("delete")}>Delete</Button>}
            {perms.can_restore && <Button size="sm" onClick={() => setConfirm("restore")}>Restore</Button>}
            {perms.can_restore && <Button size="sm" variant="danger" onClick={() => setConfirm("purge")}>Delete permanently</Button>}
            {!Object.values(perms).some(Boolean) && <p className="text-sm text-fg-muted">No lifecycle actions available.</p>}
          </div>
        </Card>
      </div>

      {editing && (
        <ProjectFormModal open project={project} onClose={() => setEditing(false)} onSaved={(saved) => { setEditing(false); onChanged(saved); notify("Project updated."); }} />
      )}
      <Modal
        open={requesting}
        title="Request archival"
        onClose={() => setRequesting(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRequesting(false)}>Cancel</Button>
            <Button
              loading={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  onChanged(await requestArchive(project.id, reason));
                  setRequesting(false);
                  notify("Archival requested. Supervisors have been notified.");
                } catch (err) {
                  notify(getErrorMessage(err), "error");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Send request
            </Button>
          </>
        }
      >
        <Field label="Reason (optional)">{(id) => <Textarea id={id} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}</Field>
      </Modal>
      <ConfirmDialog
        open={confirm !== null}
        title={humanize(confirm ?? "")}
        message={confirm ? confirmText[confirm] : ""}
        confirmLabel={humanize(confirm ?? "")}
        danger={confirm === "delete" || confirm === "purge"}
        busy={busy}
        onConfirm={() => void run()}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
