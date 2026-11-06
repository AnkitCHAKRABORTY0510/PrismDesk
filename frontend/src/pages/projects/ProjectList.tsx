import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Button,
  Card,
  DataTable,
  ErrorMessage,
  FilterSelect,
  Loading,
  Pagination,
  SearchInput,
  StatusBadge,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { formatDate, humanize } from "../../lib/format";
import { can } from "../../lib/permissions";
import { listProjects } from "../../services/projectService";
import ProjectFormModal from "./ProjectFormModal";

export default function ProjectList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [mine, setMine] = useState(false);
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const q = useDebounced(search);
  const isAdmin = can(user, "projects.view_all");

  const { data, loading, error, reload } = useAsync(
    () => listProjects({ search: q, status, mine: mine || undefined, page, page_size: 20 }),
    [q, status, mine, page]
  );

  const statusOptions = [
    { value: "active", label: "Active" },
    { value: "archived", label: "Archived" },
    ...(isAdmin ? [{ value: "deleted", label: "Deleted (recoverable)" }] : []),
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        description={isAdmin ? "All laboratory projects." : "Projects you belong to or supervise."}
        actions={can(user, "projects.create") && <Button onClick={() => setCreating(true)}>New project</Button>}
      />
      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search projects…" />
          <FilterSelect label="Project status" value={status} allLabel="Active and archived" onChange={(v) => { setStatus(v); setPage(1); }} options={statusOptions} />
          {isAdmin && (
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={mine} onChange={(e) => { setMine(e.target.checked); setPage(1); }} /> Only my projects
            </label>
          )}
        </div>
        <ErrorMessage message={error} onRetry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <>
              <DataTable
                rows={data.items}
                rowKey={(row) => row.id}
                empty="No projects found."
                onRowClick={(row) => navigate(`/projects/${row.id}`)}
                columns={[
                  {
                    header: "Project",
                    cell: (row) => (
                      <div>
                        <Link to={`/projects/${row.id}`} onClick={(e) => e.stopPropagation()} className="font-medium text-slate-800 hover:text-brand">
                          {row.title}
                        </Link>
                        <div className="line-clamp-1 text-xs text-slate-500">{row.description}</div>
                      </div>
                    ),
                  },
                  { header: "Owner", cell: (row) => row.owner.full_name },
                  { header: "My role", cell: (row) => humanize(row.my_role ?? (isAdmin ? "administrator" : "—")) },
                  { header: "Members", cell: (row) => row.member_count },
                  { header: "Status", cell: (row) => <StatusBadge status={row.status} /> },
                  { header: "Updated", cell: (row) => formatDate(row.updated_at) },
                ]}
              />
              <Pagination page={page} pageSize={20} total={data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>
      {creating && (
        <ProjectFormModal
          open
          onClose={() => setCreating(false)}
          onSaved={(project) => {
            setCreating(false);
            notify("Project created.");
            navigate(`/projects/${project.id}`);
          }}
        />
      )}
    </div>
  );
}
