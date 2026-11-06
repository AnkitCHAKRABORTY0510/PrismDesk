import { useState } from "react";

import { PageHeader } from "../../components/layout/PageHeader";
import { Card, DataTable, ErrorMessage, FilterSelect, Loading, Pagination, SearchInput } from "../../components/ui";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { formatDateTime, humanize } from "../../lib/format";
import { auditLogs } from "../../services/dashboardService";

const ENTITY_TYPES = ["user", "project", "research_paper", "task", "handbook_entry", "conference", "notification", "announcement"];

export default function AuditLogs() {
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [page, setPage] = useState(1);
  const debouncedAction = useDebounced(action);
  const { data, loading, error, reload } = useAsync(
    () => auditLogs({ action: debouncedAction, entity_type: entityType, page, page_size: 25 }),
    [debouncedAction, entityType, page]
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Logs" description="Append-only history of administrative and project actions." />
      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <SearchInput
            label="Action"
            value={action}
            onChange={(value) => {
              setAction(value);
              setPage(1);
            }}
            placeholder="Exact action, e.g. user.approved"
          />
          <FilterSelect
            label="Entity type"
            value={entityType}
            allLabel="All entities"
            onChange={(value) => {
              setEntityType(value);
              setPage(1);
            }}
            options={ENTITY_TYPES.map((type) => ({ value: type, label: humanize(type) }))}
          />
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
                columns={[
                  { header: "When", cell: (row) => formatDateTime(row.created_at) },
                  { header: "Actor", cell: (row) => row.actor_username ?? "system" },
                  { header: "Action", cell: (row) => <code className="text-xs">{row.action}</code> },
                  { header: "Entity", cell: (row) => `${humanize(row.entity_type)} ${row.entity_id?.slice(0, 8) ?? ""}` },
                  {
                    header: "Details",
                    cell: (row) => (
                      <span className="text-xs text-slate-500">
                        {Object.entries(row.details)
                          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.length + " items" : String(value)}`)
                          .join(" · ")}
                      </span>
                    ),
                  },
                ]}
              />
              <Pagination page={page} pageSize={25} total={data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>
    </div>
  );
}
