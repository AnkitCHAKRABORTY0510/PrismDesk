import { useState } from "react";

import { Badge, ErrorMessage, Loading, Modal } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime } from "../../lib/format";
import type { Version } from "../../services/handbookService";

type FieldList = readonly (readonly [string, string])[];

function show(value: unknown): string {
  if (Array.isArray(value)) return value.join("\n");
  if (value === null || value === undefined) return "";
  return String(value);
}

// Readable edit history: newest first, the current version labelled and
// the fields that changed in each save highlighted against the save before.
export function VersionHistory({
  title = "Edit history",
  load,
  fields,
  onClose,
}: {
  title?: string;
  load: () => Promise<Version[]>;
  fields: FieldList;
  onClose: () => void;
}) {
  const versions = useAsync(load, []);
  const [showAll, setShowAll] = useState(false);
  const list = [...(versions.data ?? [])].sort((a, b) => b.version - a.version);

  return (
    <Modal open wide title={title} onClose={onClose}>
      <ErrorMessage message={versions.error} />
      {versions.loading && !versions.data ? (
        <Loading />
      ) : (
        <>
          <label className="flex items-center gap-2 text-sm text-fg-muted">
            <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} className="h-4 w-4 accent-[var(--primary)]" />
            Show unchanged fields
          </label>
          <ol className="relative space-y-4 border-l-2 border-line pl-5">
            {list.map((version, index) => {
              const previous = list[index + 1];
              return (
                <li key={version.version} className="relative">
                  <span aria-hidden="true" className={`absolute -left-[1.6rem] top-1.5 h-3 w-3 rounded-full border-2 border-surface-raised ${index === 0 ? "bg-brand" : "bg-line-strong"}`} />
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold text-fg">Version {version.version}</span>
                    {index === 0 && <Badge tone="blue">Current</Badge>}
                    {!previous && <Badge>First saved</Badge>}
                    <span className="text-xs text-fg-muted">{formatDateTime(version.edited_at)}</span>
                  </div>
                  <div className="space-y-2">
                    {fields.map(([key, label]) => {
                      const value = show(version.snapshot[key]);
                      const changed = previous ? value !== show(previous.snapshot[key]) : value !== "";
                      if (!changed && !showAll) return null;
                      return (
                        <div
                          key={key}
                          className={`rounded-lg border p-3 text-sm ${changed ? "border-info-line bg-info-soft" : "border-line"}`}
                        >
                          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-fg-muted">
                            {label}
                            {changed && previous && <span className="text-info-fg">· changed</span>}
                          </div>
                          {previous && changed && show(previous.snapshot[key]) && (
                            <p className="mb-1 whitespace-pre-line text-fg-subtle line-through decoration-danger/60">{show(previous.snapshot[key])}</p>
                          )}
                          <p className="whitespace-pre-line text-fg-soft">{value || <em className="text-fg-subtle">Empty</em>}</p>
                        </div>
                      );
                    })}
                    {previous && !showAll && fields.every(([key]) => show(version.snapshot[key]) === show(previous.snapshot[key])) && (
                      <p className="text-xs text-fg-muted">No visible changes in this save.</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Modal>
  );
}
