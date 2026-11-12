import type { ReactNode } from "react";

import { Button } from "./primitives";

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "No records found.",
  onRowClick,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  empty?: string;
  onRowClick?: (row: T) => void;
}) {
  return (
    <div className="max-w-full overflow-x-auto overscroll-x-contain rounded-xl border border-line bg-surface">
      <table className="min-w-full divide-y divide-line text-sm">
        <thead className="bg-surface-muted">
          <tr>
            {columns.map((column) => (
              <th
                key={column.header}
                scope="col"
                className="whitespace-nowrap px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-fg-muted"
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line bg-surface">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-10 text-center text-fg-muted">
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={onRowClick ? "cursor-pointer transition-colors hover:bg-surface-muted" : "transition-colors hover:bg-surface-muted/50"}
              >
                {columns.map((column) => (
                  <td key={column.header} className={`px-4 py-3 align-top text-fg-soft ${column.className ?? ""}`}>
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total === 0) return null;
  return (
    <nav aria-label="Pagination" className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-fg-muted">
      <span>
        {total} result{total === 1 ? "" : "s"} · page {page} of {pages}
      </span>
      <div className="flex gap-2">
        <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </Button>
        <Button size="sm" variant="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </Button>
      </div>
    </nav>
  );
}
