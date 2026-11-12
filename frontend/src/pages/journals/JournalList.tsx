import { useState } from "react";
import { useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorMessage,
  ExternalLink,
  FilterSelect,
  Loading,
  Pagination,
  SearchInput,
  Tabs,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { useNow } from "../../hooks/useNow";
import { countdown, formatDateTime } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import { deleteJournal, listJournals, type Journal } from "../../services/journalService";
import { QUARTILE_TONES, deadlineTone, formatNumber } from "./badges";
import JournalCatalog from "./JournalCatalog";
import JournalFormModal from "./JournalFormModal";

type JournalTab = "mine" | "browse";

function JournalCards({
  items,
  onEdit,
  onDelete,
}: {
  items: Journal[];
  onEdit: (journal: Journal) => void;
  onDelete: (journal: Journal) => void;
}) {
  const now = useNow();
  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {items.map((j) => (
        <li key={j.id} className="flex flex-col rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="font-semibold text-fg">{j.title}</h3>
              <p className="text-xs text-fg-muted">{[j.publisher, j.issn].filter(Boolean).join(" · ")}</p>
            </div>
            {j.submission_deadline ? (
              <Badge tone={j.is_overdue ? "red" : deadlineTone(j.submission_deadline, now)}>
                {countdown(j.submission_deadline, now)}
              </Badge>
            ) : (
              <Badge tone="blue">Rolling</Badge>
            )}
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {j.sjr_quartile && <Badge tone={QUARTILE_TONES[j.sjr_quartile]}>{j.sjr_quartile}</Badge>}
            {j.sjr !== null && <Badge tone="violet">SJR {formatNumber(j.sjr, 2)}</Badge>}
            {j.h_index !== null && <Badge tone="slate">h-index {j.h_index}</Badge>}
            {j.is_open_access && <Badge tone="green">Open access</Badge>}
            {j.project_title && <Badge tone="slate">Project: {j.project_title}</Badge>}
          </div>
          <p className="mt-2 text-sm text-fg-soft">
            {j.submission_deadline ? (
              <>
                {j.special_issue_title ? `Special issue “${j.special_issue_title}”` : "Special issue"} deadline:{" "}
                {formatDateTime(j.submission_deadline)}
              </>
            ) : (
              "Rolling submissions (no deadline)"
            )}
          </p>
          {j.subject_areas.length > 0 && <p className="mt-1 text-xs text-fg-muted">{j.subject_areas.join(" · ")}</p>}
          {j.notes && <p className="mt-2 line-clamp-3 whitespace-pre-line text-xs text-fg-muted">{j.notes}</p>}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {j.homepage_url && <ExternalLink href={j.homepage_url}>Homepage</ExternalLink>}
            <ExternalLink href={j.google_special_issues_url}>Find special issues</ExternalLink>
            <ExternalLink href={j.wikicfp_url}>WikiCFP</ExternalLink>
          </div>
          <div className="mt-auto flex gap-2 pt-3">
            <Button size="sm" variant="secondary" onClick={() => onEdit(j)}>
              {j.submission_deadline ? "Edit" : "Edit / add special issue"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => onDelete(j)}>Remove</Button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function JournalList() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [params, setParams] = useSearchParams();
  const tab: JournalTab = params.get("tab") === "browse" ? "browse" : "mine";
  const [search, setSearch] = useState("");
  const [deadline, setDeadline] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Journal | "new" | null>(null);
  const [removing, setRemoving] = useState<Journal | null>(null);
  const q = useDebounced(search);
  const canCreate = can(user, "journals.create");

  const data = useAsync(() => listJournals({ search: q, deadline, page, page_size: 20 }), [q, deadline, page]);

  const remove = async (journal: Journal) => {
    try {
      await deleteJournal(journal.id);
      notify("Journal removed from your list.");
      void data.reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Journals"
        description="Your personal list of target journals. Most journals accept submissions year round; track special-issue deadlines when you need them."
        actions={canCreate && <Button onClick={() => setEditing("new")}>Add journal</Button>}
      />
      <Tabs<JournalTab>
        tabs={[
          { id: "mine", label: "My journals" },
          { id: "browse", label: "Browse journals" },
        ]}
        active={tab}
        onChange={(id) => setParams(id === "browse" ? { tab: "browse" } : {}, { replace: true })}
      />
      {tab === "browse" ? (
        <Card>
          <JournalCatalog onAdded={() => void data.reload()} />
        </Card>
      ) : (
        <Card>
          <div className="mb-4 flex flex-wrap gap-3">
            <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search title, publisher, ISSN, special issue…" />
            <FilterSelect
              label="Submission type"
              value={deadline}
              allLabel="All journals"
              onChange={(v) => { setDeadline(v); setPage(1); }}
              options={[{ value: "special", label: "Special-issue deadlines" }, { value: "rolling", label: "Rolling submissions" }]}
            />
          </div>
          <ErrorMessage message={data.error} onRetry={data.reload} />
          {data.loading && !data.data ? (
            <Loading />
          ) : (
            data.data &&
            (data.data.items.length === 0 ? (
              <EmptyState
                title={q || deadline ? "No journals match" : "No journals yet"}
                description={canCreate ? "Browse ranked journals and add the ones you plan to submit to." : undefined}
                action={
                  canCreate && !q && !deadline ? (
                    <Button variant="secondary" onClick={() => setParams({ tab: "browse" }, { replace: true })}>Browse journals</Button>
                  ) : undefined
                }
              />
            ) : (
              <>
                <JournalCards items={data.data.items} onEdit={(j) => setEditing(j)} onDelete={setRemoving} />
                <Pagination page={page} pageSize={20} total={data.data.total} onChange={setPage} />
              </>
            ))
          )}
        </Card>
      )}
      {editing && (
        <JournalFormModal
          open
          journal={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            notify("Journal saved.");
            void data.reload();
          }}
        />
      )}
      <ConfirmDialog
        open={removing !== null}
        title="Remove journal"
        message={`Remove ${removing?.title} from your list?`}
        confirmLabel="Remove"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={async () => {
          if (removing) await remove(removing);
          setRemoving(null);
        }}
      />
    </div>
  );
}
