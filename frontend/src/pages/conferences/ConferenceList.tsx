import { useState } from "react";
import { useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
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
import {
  archiveConferenceLink,
  deleteConference,
  listConferences,
  unlinkConference,
  type Conference,
} from "../../services/conferenceService";
import ConferenceCatalog from "./ConferenceCatalog";
import ConferenceFormModal from "./ConferenceFormModal";

type ConferenceTab = "mine" | "browse";

export function ConferenceCards({
  items,
  onEdit,
  onChanged,
  projectId,
}: {
  items: Conference[];
  onEdit?: (conference: Conference) => void;
  onChanged: () => void;
  projectId?: string;
}) {
  const now = useNow();
  const { notify } = useToast();
  const { user } = useAuth();
  const [deleting, setDeleting] = useState<Conference | null>(null);

  const linkAction = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      notify(message);
      onChanged();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  if (items.length === 0) return <p className="py-6 text-center text-sm text-fg-muted">No conferences found.</p>;

  return (
    <>
      <ul className="grid gap-4 md:grid-cols-2">
        {items.map((c) => {
          const overdue = new Date(c.submission_deadline) < now;
          const links = projectId ? c.projects.filter((p) => p.project_id === projectId) : c.projects;
          return (
            <li key={c.id} className="rounded-xl border border-line bg-surface p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-fg">{c.name}</h3>
                  <p className="text-xs text-fg-muted">{[c.acronym, c.location].filter(Boolean).join(" · ")}</p>
                </div>
                <Badge tone={overdue ? "red" : "amber"}>{countdown(c.submission_deadline, now)}</Badge>
              </div>
              <p className="mt-2 text-sm text-fg-soft">Submission deadline: {formatDateTime(c.submission_deadline)}</p>
              {c.important_dates.length > 0 && (
                <ul className="mt-2 text-xs text-fg-muted">
                  {c.important_dates.map((d) => (
                    <li key={d.label + d.date}>{d.label}: {formatDateTime(d.date)}</li>
                  ))}
                </ul>
              )}
              <div className="mt-2 flex flex-wrap gap-3 text-sm">
                {c.website_url && <ExternalLink href={c.website_url}>Website</ExternalLink>}
                {c.cfp_url && <ExternalLink href={c.cfp_url}>Call for papers</ExternalLink>}
              </div>
              {links.length > 0 && (
                <ul className="mt-3 space-y-1 text-xs">
                  {links.map((link) => (
                    <li key={link.project_id} className="flex items-center justify-between gap-2">
                      <span>
                        {link.project_title} {link.status === "archived" && <Badge>archived</Badge>}
                      </span>
                      {link.can_manage && (
                        <span className="flex gap-2">
                          {link.status === "active" && (
                            <button type="button" className="text-fg-muted hover:text-link" onClick={() => void linkAction(() => archiveConferenceLink(c.id, link.project_id), "Association archived.")}>
                              Archive
                            </button>
                          )}
                          <button type="button" className="text-fg-muted hover:text-danger-fg" onClick={() => void linkAction(() => unlinkConference(c.id, link.project_id), "Removed from project.")}>
                            Remove
                          </button>
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-3 flex gap-2">
                {c.can_edit && onEdit && <Button size="sm" variant="secondary" onClick={() => onEdit(c)}>Edit</Button>}
                {(user?.roles.includes("Administrator") || (c.added_by === user?.id && c.projects.every((p) => p.status !== "active"))) && (
                  <Button size="sm" variant="ghost" onClick={() => setDeleting(c)}>Delete</Button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      <ConfirmDialog
        open={deleting !== null}
        title="Delete conference"
        message={`Delete ${deleting?.name} for every project?`}
        confirmLabel="Delete"
        danger
        onCancel={() => setDeleting(null)}
        onConfirm={async () => {
          if (deleting) await linkAction(() => deleteConference(deleting.id), "Conference deleted.");
          setDeleting(null);
        }}
      />
    </>
  );
}

export default function ConferenceList() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [search, setSearch] = useState("");
  const [timing, setTiming] = useState("upcoming");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Conference | "new" | null>(null);
  const [params, setParams] = useSearchParams();
  const tab: ConferenceTab = params.get("tab") === "browse" ? "browse" : "mine";
  const q = useDebounced(search);

  const data = useAsync(
    () =>
      listConferences({
        search: q,
        timing,
        deadline_from: from ? new Date(from).toISOString() : undefined,
        deadline_to: to ? new Date(`${to}T23:59:59`).toISOString() : undefined,
        page,
        page_size: 20,
      }),
    [q, timing, from, to, page]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Conference Tracker"
        description="Deadlines are shown in your local timezone. One conference record is shared by every project that targets it."
        actions={can(user, "conferences.create") && <Button onClick={() => setEditing("new")}>Add conference</Button>}
      />
      <Tabs<ConferenceTab>
        tabs={[
          { id: "mine", label: "My conferences" },
          { id: "browse", label: "Browse conferences" },
        ]}
        active={tab}
        onChange={(id) => setParams(id === "browse" ? { tab: "browse" } : {}, { replace: true })}
      />
      {tab === "browse" ? (
        <Card>
          <ConferenceCatalog onAdded={() => void data.reload()} />
        </Card>
      ) : (
        <Card>
          <div className="mb-4 flex flex-wrap gap-3">
            <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search name, acronym, location…" />
            <FilterSelect
              label="Deadline timing"
              value={timing}
              allLabel="All deadlines"
              onChange={(v) => { setTiming(v); setPage(1); }}
              options={[{ value: "upcoming", label: "Upcoming" }, { value: "overdue", label: "Passed" }]}
            />
            <input aria-label="Deadline from" type="date" className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg sm:w-auto" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1); }} />
            <input aria-label="Deadline to" type="date" className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg sm:w-auto" value={to} onChange={(e) => { setTo(e.target.value); setPage(1); }} />
          </div>
          <ErrorMessage message={data.error} onRetry={data.reload} />
          {data.loading && !data.data ? (
            <Loading />
          ) : (
            data.data && (
              <>
                <ConferenceCards items={data.data.items} onEdit={(c) => setEditing(c)} onChanged={() => void data.reload()} />
                <Pagination page={page} pageSize={20} total={data.data.total} onChange={setPage} />
              </>
            )
          )}
        </Card>
      )}
      {editing && (
        <ConferenceFormModal
          open
          conference={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            notify("Conference saved.");
            void data.reload();
          }}
        />
      )}
    </div>
  );
}
