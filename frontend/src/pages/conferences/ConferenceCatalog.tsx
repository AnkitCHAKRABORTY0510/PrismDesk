import { useState } from "react";
import { Check, Plus, RefreshCw } from "lucide-react";

import {
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
import { useNow } from "../../hooks/useNow";
import { countdown, formatDateTime } from "../../lib/format";
import { can } from "../../lib/permissions";
import { getErrorMessage } from "../../services/api";
import {
  addCatalogConference,
  browseConferenceCatalog,
  refreshConferenceCatalog,
  type CatalogConference,
} from "../../services/conferenceService";

const PAGE_SIZE = 25;
const DAY_MS = 86_400_000;

type Tone = "green" | "amber" | "red" | "blue" | "violet" | "slate";

const RANK_TONES: Record<string, Tone> = { "A*": "violet", A: "blue", B: "green", C: "slate" };

function deadlineTone(deadline: string, now: Date): Tone {
  const left = new Date(deadline).getTime() - now.getTime();
  if (left < 7 * DAY_MS) return "red";
  if (left < 30 * DAY_MS) return "amber";
  return "blue";
}

function CatalogRow({
  item,
  now,
  topicLabels,
  canAdd,
  adding,
  onAdd,
}: {
  item: CatalogConference;
  now: Date;
  topicLabels: Record<string, string>;
  canAdd: boolean;
  adding: boolean;
  onAdd: () => void;
}) {
  const otherRounds = item.timeline.filter((t) => t.deadline && t.deadline !== item.next_deadline);
  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-fg">
            {item.acronym} {item.year}
          </h3>
          {item.core_rank && <Badge tone={RANK_TONES[item.core_rank] ?? "slate"}>CORE {item.core_rank}</Badge>}
          {item.ccf_rank && <Badge tone="slate">CCF {item.ccf_rank}</Badge>}
          {item.category_label && <span className="text-xs text-fg-subtle">{item.category_label}</span>}
        </div>
        <p className="text-sm text-fg-soft">{item.name}</p>
        {item.topics.length > 0 && (
          <ul className="flex flex-wrap gap-1" aria-label="Topics">
            {item.topics.map((t) => (
              <li key={t} className="rounded-md border border-line bg-surface-muted px-1.5 py-0.5 text-[11px] text-fg-soft">
                {topicLabels[t] ?? t}
              </li>
            ))}
          </ul>
        )}
        {(item.conference_dates || item.place) && (
          <p className="text-xs text-fg-muted">
            {[item.conference_dates, item.place].filter((v) => v && v !== "TBD").join(" · ") || "Dates and place to be announced"}
          </p>
        )}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {item.website_url && <ExternalLink href={item.website_url}>Official site</ExternalLink>}
          <ExternalLink href={item.wikicfp_url}>Call for papers (WikiCFP)</ExternalLink>
          {item.dblp_url && <ExternalLink href={item.dblp_url}>DBLP</ExternalLink>}
        </div>
      </div>

      <div className="flex shrink-0 flex-col gap-2 md:w-72 md:items-end md:text-right">
        {item.deadline_status === "upcoming" && item.next_deadline ? (
          <>
            <div className="flex flex-wrap items-center gap-2 md:justify-end">
              <Badge tone={deadlineTone(item.next_deadline, now)}>{countdown(item.next_deadline, now)}</Badge>
            </div>
            <p className="text-xs text-fg-soft">
              Deadline: {formatDateTime(item.next_deadline)}
              {item.next_deadline_comment && <span className="block text-fg-muted">{item.next_deadline_comment}</span>}
            </p>
            {item.next_abstract_deadline && item.next_abstract_deadline !== item.next_deadline && (
              <p className="text-xs text-fg-muted">Abstract: {formatDateTime(item.next_abstract_deadline)}</p>
            )}
            {otherRounds.length > 0 && (
              <p className="text-xs text-fg-subtle">
                +{otherRounds.length} other round{otherRounds.length === 1 ? "" : "s"}
              </p>
            )}
          </>
        ) : item.deadline_status === "tbd" ? (
          <Badge tone="slate">Deadline TBD</Badge>
        ) : (
          <Badge tone="slate">No upcoming deadline</Badge>
        )}
        {canAdd &&
          (item.in_my_list ? (
            <Button size="sm" variant="secondary" disabled aria-label={`${item.acronym} ${item.year ?? ""} is in your list`}>
              <Check className="h-4 w-4" aria-hidden="true" /> Added
            </Button>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              loading={adding}
              disabled={item.deadline_status !== "upcoming"}
              title={item.deadline_status !== "upcoming" ? "The deadline has not been announced yet." : undefined}
              onClick={onAdd}
            >
              <Plus className="h-4 w-4" aria-hidden="true" /> Add to my list
            </Button>
          ))}
      </div>
    </li>
  );
}

export default function ConferenceCatalog({ onAdded }: { onAdded?: () => void }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const now = useNow();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [topic, setTopic] = useState("prism");
  const [coreRank, setCoreRank] = useState("");
  const [ccfRank, setCcfRank] = useState("");
  const [upcomingOnly, setUpcomingOnly] = useState(true);
  const [sort, setSort] = useState("deadline");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const q = useDebounced(search);

  const data = useAsync(
    () =>
      browseConferenceCatalog({
        q,
        topic,
        category,
        core_rank: coreRank,
        ccf_rank: ccfRank,
        upcoming_only: upcomingOnly,
        sort,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
    [q, topic, category, coreRank, ccfRank, upcomingOnly, sort, page]
  );

  const filter = <T,>(setter: (value: T) => void) => (value: T) => {
    setter(value);
    setPage(1);
  };

  const add = async (item: CatalogConference) => {
    setAdding(item.key);
    try {
      const conference = await addCatalogConference(item.key);
      notify(conference.linked_existing ? `${conference.name} is already in your list.` : `Added ${conference.name} to your conferences.`);
      if (data.data) {
        data.setData({
          ...data.data,
          items: data.data.items.map((i) => (i.key === item.key ? { ...i, in_my_list: true, my_conference_id: conference.id } : i)),
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
      const result = await refreshConferenceCatalog();
      notify(result.stale ? "Could not reach the data source; showing the saved copy." : "Conference catalog updated.", result.stale ? "error" : "success");
      await data.reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setRefreshing(false);
    }
  };

  const canAdd = can(user, "conferences.create");
  const categories = data.data?.categories ?? [];
  const topics = data.data?.topics ?? [];
  const topicLabels = Object.fromEntries(topics.map((t) => [t.id, t.label]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <SearchInput value={search} onChange={filter(setSearch)} placeholder="Search acronym, name, place, topic…" />
        <FilterSelect
          label="Topic"
          value={topic}
          allLabel="All topics"
          onChange={filter(setTopic)}
          options={[
            { value: "prism", label: "PRISM focus" },
            ...topics.map((t) => ({ value: t.id, label: t.label })),
          ]}
        />
        <FilterSelect
          label="Category"
          value={category}
          allLabel="All categories"
          onChange={filter(setCategory)}
          options={categories.map((c) => ({ value: c.code, label: c.label }))}
        />
        <FilterSelect
          label="CORE rank"
          value={coreRank}
          allLabel="Any CORE rank"
          onChange={filter(setCoreRank)}
          options={["A*", "A", "B", "C"].map((r) => ({ value: r, label: `CORE ${r}` }))}
        />
        <FilterSelect
          label="CCF rank"
          value={ccfRank}
          allLabel="Any CCF rank"
          onChange={filter(setCcfRank)}
          options={["A", "B", "C"].map((r) => ({ value: r, label: `CCF ${r}` }))}
        />
        <select
          aria-label="Sort"
          value={sort}
          onChange={(e) => filter(setSort)(e.target.value)}
          className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg sm:w-auto"
        >
          <option value="deadline">Nearest deadline</option>
          <option value="name">Name (A–Z)</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-fg-soft">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-line-strong accent-[var(--primary)]"
            checked={upcomingOnly}
            onChange={(e) => filter(setUpcomingOnly)(e.target.checked)}
          />
          Upcoming only
        </label>
      </div>

      <ErrorMessage message={data.error} onRetry={data.reload} />
      {data.loading && !data.data ? (
        <SkeletonRows rows={6} label="Loading conference catalog…" />
      ) : (
        data.data &&
        (data.data.items.length === 0 ? (
          <EmptyState
            title="No conferences match"
            description={
              topic === "prism"
                ? "Nothing in the PRISM focus matches. Try “All topics”, clear filters, or include passed deadlines."
                : upcomingOnly
                  ? "Try clearing filters or include conferences whose deadline has passed."
                  : "Try a different search or clear the filters."
            }
          />
        ) : (
          <div className={data.loading ? "opacity-60 transition-opacity" : undefined}>
            <ul className="divide-y divide-line">
              {data.data.items.map((item) => (
                <CatalogRow
                  key={item.key}
                  item={item}
                  now={now}
                  topicLabels={topicLabels}
                  canAdd={canAdd}
                  adding={adding === item.key}
                  onAdd={() => void add(item)}
                />
              ))}
            </ul>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.data.total} onChange={setPage} />
          </div>
        ))
      )}

      {data.data && (
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 text-xs text-fg-muted">
          <span>
            Data: <ExternalLink href={data.data.source.url}>ccfddl/ccf-deadlines</ExternalLink> ({data.data.source.license}), CORE ranks via
            ccfddl · Updated {formatDateTime(data.data.fetched_at)}
            {data.data.stale && <span className="text-warn-fg"> · offline copy</span>}. Always confirm dates on the official site.
          </span>
          <Button size="sm" variant="ghost" loading={refreshing} onClick={() => void refresh()}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Refresh
          </Button>
        </footer>
      )}
    </div>
  );
}
