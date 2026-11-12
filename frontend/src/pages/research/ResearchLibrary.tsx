import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  ErrorMessage,
  FilterSelect,
  Input,
  Loading,
  Pagination,
  SearchInput,
  StatusBadge,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import { ReadingStatusToggle } from "../../components/research/ReadingStatusToggle";
import { deletePaper, listPapers, type Paper } from "../../services/researchService";
import PaperFormModal from "./PaperFormModal";

export default function ResearchLibrary() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { notify } = useToast();
  // Filters live in the URL so "Back to library" on a paper restores them.
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  const author = params.get("author") ?? "";
  const year = params.get("year") ?? "";
  const status = params.get("status") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const setFilter = (key: string, value: string) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(key, value);
        else next.delete(key);
        if (key !== "page") next.delete("page");
        return next;
      },
      { replace: true }
    );
  const setPage = (value: number) => setFilter("page", value > 1 ? String(value) : "");
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Paper | null>(null);
  const [busy, setBusy] = useState(false);
  const openPaper = (id: string) => navigate(`/research/papers/${id}`, { state: { backTo: `${location.pathname}${location.search}` } });
  const q = useDebounced(search);
  const tracks = can(user, "research.track_progress");
  const a = useDebounced(author);
  const y = useDebounced(year);

  const { data, loading, error, reload, setData } = useAsync(
    () =>
      listPapers({
        search: q,
        author: a,
        year: /^\d{4}$/.test(y) ? y : undefined,
        reading_status: status,
        page,
        page_size: 20,
      }),
    [q, a, y, status, page]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research Library"
        description="Shared paper metadata for the whole lab. Papers link to projects; files stay with the publisher."
        actions={can(user, "research.create") && <Button onClick={() => setAdding(true)}>Add paper</Button>}
      />
      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <SearchInput value={search} onChange={(v) => setFilter("search", v)} placeholder="Search title, abstract, keywords, DOI…" />
          <Input aria-label="Author" placeholder="Author" className="w-40" value={author} onChange={(e) => setFilter("author", e.target.value)} />
          <Input aria-label="Publication year" placeholder="Year" className="w-24" value={year} onChange={(e) => setFilter("year", e.target.value)} />
          {can(user, "research.track_progress") && (
            <FilterSelect
              label="My reading status"
              value={status}
              allLabel="Any reading status"
              onChange={(v) => setFilter("status", v)}
              options={[
                { value: "not_started", label: "To read" },
                { value: "reading", label: "Reading" },
                { value: "completed", label: "Completed" },
              ]}
            />
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
                empty="No papers match these filters."
                onRowClick={(row) => openPaper(row.id)}
                columns={[
                  {
                    header: "Title",
                    cell: (row) => (
                      <div>
                        <Link to={`/research/papers/${row.id}`} state={{ backTo: `${location.pathname}${location.search}` }} className="font-medium text-fg hover:text-link" onClick={(e) => e.stopPropagation()}>
                          {row.title}
                        </Link>
                        <div className="text-xs text-fg-muted">{row.authors.join(", ")}</div>
                      </div>
                    ),
                  },
                  { header: "Year", cell: (row) => row.publication_year ?? "—" },
                  { header: "Venue", cell: (row) => row.venue ?? "—" },
                  { header: "Projects", cell: (row) => row.projects.map((p) => p.title).join(", ") || "—" },
                  {
                    header: "My status",
                    cell: (row) =>
                      tracks ? (
                        <ReadingStatusToggle
                          compact
                          paperId={row.id}
                          paperTitle={row.title}
                          status={row.my_status}
                          onChange={(next) =>
                            setData({ ...data, items: data.items.map((p) => (p.id === row.id ? { ...p, my_status: next } : p)) })
                          }
                        />
                      ) : (
                        <StatusBadge status={row.my_status ?? "not_started"} />
                      ),
                  },
                  {
                    header: "Actions",
                    cell: (row) =>
                      row.can_edit && (
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Delete ${row.title}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setRemoving(row);
                          }}
                        >
                          Delete
                        </Button>
                      ),
                  },
                ]}
              />
              <Pagination page={page} pageSize={20} total={data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>
      <ConfirmDialog
        open={removing !== null}
        title="Delete paper"
        message={`Delete “${removing?.title ?? ""}”? This can't be undone.`}
        confirmLabel="Delete"
        danger
        busy={busy}
        onCancel={() => setRemoving(null)}
        onConfirm={async () => {
          if (!removing) return;
          setBusy(true);
          try {
            await deletePaper(removing.id);
            notify("Paper deleted.");
            setRemoving(null);
            await reload();
          } catch (err) {
            notify(getErrorMessage(err), "error");
          } finally {
            setBusy(false);
          }
        }}
      />
      {adding && (
        <PaperFormModal
          open
          onClose={() => setAdding(false)}
          onSaved={(paper) => {
            setAdding(false);
            notify("Paper added to the library.");
            navigate(`/research/papers/${paper.id}`);
          }}
        />
      )}
    </div>
  );
}
