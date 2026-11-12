import { useState } from "react";
import { Check, Plus, RefreshCw } from "lucide-react";

import {
  Alert,
  Badge,
  Button,
  EmptyState,
  ErrorMessage,
  ExternalLink,
  FilterSelect,
  Pagination,
  SearchInput,
  SkeletonRows,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { formatDateTime } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import {
  addCatalogJournal,
  browseJournalCatalog,
  refreshJournalCatalog,
  type CatalogJournal,
} from "../../services/journalService";
import { QUARTILE_TONES, formatNumber } from "./badges";

const PAGE_SIZE = 25;

function CatalogRow({
  item,
  domainLabels,
  canAdd,
  adding,
  onAdd,
}: {
  item: CatalogJournal;
  domainLabels: Record<string, string>;
  canAdd: boolean;
  adding: boolean;
  onAdd: () => void;
}) {
  const details = [item.publisher, item.country, item.issns.slice(0, 2).join(", ")].filter(Boolean).join(" · ");
  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0 flex-1 space-y-1.5">
        <h3 className="font-semibold text-fg">{item.title}</h3>
        <div className="flex flex-wrap items-center gap-1.5">
          {item.sjr_quartile && <Badge tone={QUARTILE_TONES[item.sjr_quartile]}>{item.sjr_quartile}</Badge>}
          {item.sjr !== null && <Badge tone="violet">SJR {formatNumber(item.sjr, 2)}</Badge>}
          {item.h_index !== null && <Badge tone="slate">h-index {item.h_index}</Badge>}
          {item.is_in_doaj ? <Badge tone="green">Open access · DOAJ</Badge> : item.is_oa && <Badge tone="green">Open access</Badge>}
        </div>
        {details && <p className="text-xs text-fg-muted">{details}</p>}
        {item.domains.length > 0 && (
          <ul className="flex flex-wrap gap-1" aria-label="Lab domains">
            {item.domains.map((d) => (
              <li key={d} className="rounded-md border border-line bg-surface-muted px-1.5 py-0.5 text-[11px] text-fg-soft">
                {domainLabels[d] ?? d}
              </li>
            ))}
          </ul>
        )}
        {item.categories.length > 0 && (
          <p className="text-xs text-fg-soft">
            {item.categories
              .slice(0, 4)
              .map((c) => (c.quartile ? `${c.name} (${c.quartile})` : c.name))
              .join(" · ")}
            {item.categories.length > 4 && ` · +${item.categories.length - 4} more`}
          </p>
        )}
        {item.categories.length === 0 && item.areas.length > 0 && (
          <p className="text-xs text-fg-soft">{item.areas.slice(0, 4).join(" · ")}</p>
        )}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {item.homepage_url && <ExternalLink href={item.homepage_url}>Homepage</ExternalLink>}
          <ExternalLink href={item.google_special_issues_url}>Find special issues</ExternalLink>
          <ExternalLink href={item.wikicfp_url}>WikiCFP</ExternalLink>
          {item.sjr_url && <ExternalLink href={item.sjr_url}>SJR profile</ExternalLink>}
          {item.openalex_url && <ExternalLink href={item.openalex_url}>OpenAlex</ExternalLink>}
        </div>
      </div>

      <div className="flex shrink-0 flex-col gap-2 md:w-60 md:items-end md:text-right">
        <Badge tone="blue">Rolling submissions (no deadline)</Badge>
        <dl className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5 text-xs text-fg-muted md:justify-end">
          {item.two_year_mean_citedness !== null && (
            <>
              <dt>2-yr citedness</dt>
              <dd className="text-fg-soft">{formatNumber(item.two_year_mean_citedness, 2)}</dd>
            </>
          )}
          {item.apc_usd !== null && (
            <>
              <dt>APC</dt>
              <dd className="text-fg-soft">US${formatNumber(item.apc_usd)}</dd>
            </>
          )}
        </dl>
        {canAdd &&
          (item.in_my_list ? (
            <Button size="sm" variant="secondary" disabled aria-label={`${item.title} is in your list`}>
              <Check className="h-4 w-4" aria-hidden="true" /> Added
            </Button>
          ) : (
            <Button size="sm" variant="secondary" loading={adding} disabled={!item.issn} onClick={onAdd}>
              <Plus className="h-4 w-4" aria-hidden="true" /> Add to my list
            </Button>
          ))}
      </div>
    </li>
  );
}

export default function JournalCatalog({ onAdded }: { onAdded?: () => void }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const [search, setSearch] = useState("");
  const [domain, setDomain] = useState("");
  const [quartile, setQuartile] = useState("");
  const [sort, setSort] = useState("sjr");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const q = useDebounced(search);

  const data = useAsync(
    () => browseJournalCatalog({ q, domain, quartile, sort, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    [q, domain, quartile, sort, page]
  );

  const filter = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setPage(1);
  };

  const add = async (item: CatalogJournal) => {
    if (!item.issn) return;
    setAdding(item.issn);
    try {
      const journal = await addCatalogJournal(item.issn);
      notify(journal.linked_existing ? `${journal.title} is already in your list.` : `Added ${journal.title} to your journals.`);
      if (data.data) {
        data.setData({
          ...data.data,
          items: data.data.items.map((i) => (i.issn === item.issn ? { ...i, in_my_list: true, my_journal_id: journal.id } : i)),
        });
      }
      onAdded?.();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setAdding(null);
    }
  };

  const refresh = async () => {
    setRefreshing(true);
    try {
      const result = await refreshJournalCatalog();
      if (result.ranking_available && !result.stale) notify(`Ranking data updated (${result.total.toLocaleString()} journals).`);
      else notify("SJR ranking data could not be downloaded; see the note above the list.", "error");
      await data.reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setRefreshing(false);
    }
  };

  const canAdd = can(user, "journals.create");
  const rankingAvailable = data.data?.ranking_available ?? true;
  const domainLabels = Object.fromEntries((data.data?.domains ?? []).map((d) => [d.id, d.label]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <SearchInput
          value={search}
          onChange={filter(setSearch)}
          placeholder={rankingAvailable ? "Search title, ISSN, publisher or category…" : "Search journal title or ISSN…"}
        />
        <FilterSelect
          label="Domain"
          value={domain}
          allLabel="All (lab domains)"
          onChange={filter(setDomain)}
          options={(data.data?.domains ?? []).map((d) => ({ value: d.id, label: d.label }))}
        />
        {rankingAvailable && (
          <FilterSelect
            label="SJR quartile"
            value={quartile}
            allLabel="Any quartile"
            onChange={filter(setQuartile)}
            options={["Q1", "Q2", "Q3", "Q4"].map((value) => ({ value, label: value }))}
          />
        )}
        <select
          aria-label="Sort"
          value={sort}
          onChange={(e) => filter(setSort)(e.target.value)}
          className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg sm:w-auto"
        >
          <option value="sjr">{rankingAvailable ? "SJR rank" : "h-index"}</option>
          {rankingAvailable && <option value="h_index">h-index</option>}
          <option value="relevance">Best match</option>
          <option value="title">Title (A–Z)</option>
        </select>
      </div>

      {data.data && !data.data.ranking_available && data.data.ranking.note && (
        <Alert kind="info">
          Showing OpenAlex data without SJR quartiles. {data.data.ranking.note}
        </Alert>
      )}
      {data.data && !data.data.metadata.available && (
        <Alert kind="info">OpenAlex is unreachable right now, so homepages and open-access details are missing.</Alert>
      )}

      <ErrorMessage message={data.error} onRetry={data.reload} />
      {data.loading && !data.data ? (
        <SkeletonRows rows={6} label="Loading journal catalog…" />
      ) : (
        data.data &&
        (data.data.items.length === 0 ? (
          <EmptyState title="No journals match" description="Try a different search or clear the filters." />
        ) : (
          <div className={data.loading ? "opacity-60 transition-opacity" : undefined}>
            <ul className="divide-y divide-line">
              {data.data.items.map((item, index) => (
                <CatalogRow
                  key={item.issn ?? `${item.title}-${index}`}
                  item={item}
                  domainLabels={domainLabels}
                  canAdd={canAdd}
                  adding={adding !== null && adding === item.issn}
                  onAdd={() => void add(item)}
                />
              ))}
            </ul>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.data.total} onChange={setPage} />
            {data.data.total_is_estimate && (
              <p className="mt-1 text-xs text-fg-subtle">
                The total is an estimate. OpenAlex results are narrowed to journals whose work is mostly in the lab’s domains; search or pick a domain to see more.
              </p>
            )}
          </div>
        ))
      )}

      {data.data && (
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 text-xs text-fg-muted">
          <span>
            Ranking data: <ExternalLink href={data.data.ranking.url}>{data.data.ranking.name}</ExternalLink>
            {data.data.ranking.fetched_at
              ? ` · updated ${formatDateTime(data.data.ranking.fetched_at)}${data.data.ranking.stale ? " (saved copy)" : ""}`
              : " · unavailable"}
            . Journal metadata: <ExternalLink href={data.data.metadata.url}>OpenAlex</ExternalLink> ({data.data.metadata.license}).
            Limited to the lab’s domains (computer science, architecture &amp; hardware, electronics, AI). Journals accept
            submissions year round unless you track a special issue.
          </span>
          <Button size="sm" variant="ghost" loading={refreshing} onClick={() => void refresh()}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Refresh rankings
          </Button>
        </footer>
      )}
    </div>
  );
}
