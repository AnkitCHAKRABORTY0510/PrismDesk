import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Button,
  Card,
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
import { listPapers } from "../../services/researchService";
import PaperFormModal from "./PaperFormModal";

export default function ResearchLibrary() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [search, setSearch] = useState("");
  const [author, setAuthor] = useState("");
  const [year, setYear] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(false);
  const q = useDebounced(search);
  const a = useDebounced(author);
  const y = useDebounced(year);

  const { data, loading, error, reload } = useAsync(
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
          <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search title, abstract, keywords, DOI…" />
          <Input aria-label="Author" placeholder="Author" className="w-40" value={author} onChange={(e) => { setAuthor(e.target.value); setPage(1); }} />
          <Input aria-label="Publication year" placeholder="Year" className="w-24" value={year} onChange={(e) => { setYear(e.target.value); setPage(1); }} />
          {can(user, "research.track_progress") && (
            <FilterSelect
              label="My reading status"
              value={status}
              allLabel="Any reading status"
              onChange={(v) => { setStatus(v); setPage(1); }}
              options={[
                { value: "not_started", label: "Not started" },
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
                onRowClick={(row) => navigate(`/research/papers/${row.id}`)}
                columns={[
                  {
                    header: "Title",
                    cell: (row) => (
                      <div>
                        <Link to={`/research/papers/${row.id}`} className="font-medium text-slate-800 hover:text-brand" onClick={(e) => e.stopPropagation()}>
                          {row.title}
                        </Link>
                        <div className="text-xs text-slate-500">{row.authors.join(", ")}</div>
                      </div>
                    ),
                  },
                  { header: "Year", cell: (row) => row.publication_year ?? "—" },
                  { header: "Venue", cell: (row) => row.venue ?? "—" },
                  { header: "Projects", cell: (row) => row.projects.map((p) => p.title).join(", ") || "—" },
                  { header: "My status", cell: (row) => <StatusBadge status={row.my_status ?? "not_started"} /> },
                ]}
              />
              <Pagination page={page} pageSize={20} total={data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>
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
