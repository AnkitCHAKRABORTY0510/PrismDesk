import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { useId } from "react";
import { Inbox } from "lucide-react";

import { humanize } from "../../lib/format";

function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "danger" | "ghost" | "success";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand text-link-fg shadow-sm hover:bg-brand-hover",
  secondary: "border border-line-strong bg-surface text-fg-soft shadow-sm hover:bg-surface-muted hover:text-fg",
  danger: "bg-danger text-white shadow-sm hover:bg-danger-hover",
  success: "bg-success text-white shadow-sm hover:bg-success-hover",
  ghost: "text-fg-soft hover:bg-surface-muted hover:text-fg",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" ? "h-8 px-3 text-xs" : "h-10 px-4 text-sm",
        VARIANTS[variant],
        className
      )}
      {...props}
    >
      {loading ? "Working…" : children}
    </button>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("min-w-0 rounded-xl border border-line bg-surface p-4 shadow-card sm:p-5", className)}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {title && <h2 className="text-base font-semibold text-fg">{title}</h2>}
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-line bg-surface p-4 shadow-card">
      <div className="truncate text-xs font-medium uppercase tracking-wide text-fg-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-fg">{value}</div>
      {hint && <div className="mt-1 text-xs text-fg-muted">{hint}</div>}
    </div>
  );
}

const inputClass =
  "w-full min-w-0 rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg shadow-sm transition-colors focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/25 focus-visible:outline-none disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-fg-muted";

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  children: (id: string) => ReactNode;
}

export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId();
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-fg-soft">
        {label}
      </label>
      {children(id)}
      {hint && !error && <p className="text-xs text-fg-muted">{hint}</p>}
      {error && <p className="text-xs text-danger-fg">{error}</p>}
    </div>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cx(inputClass, className)} {...props} />;
}

export function Textarea({ className, rows = 4, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={rows} className={cx(inputClass, className)} {...props} />;
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cx(inputClass, className)} {...props}>
      {children}
    </select>
  );
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  label = "Search",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}) {
  return (
    <input
      type="search"
      aria-label={label}
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      className={cx(inputClass, "basis-full sm:basis-56 flex-1")}
    />
  );
}

export function FilterSelect({
  label,
  value,
  onChange,
  options,
  allLabel = "All",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  allLabel?: string;
}) {
  return (
    <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)} className={cx(inputClass, "w-full sm:w-auto")}>
      <option value="">{allLabel}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

const BADGE_TONES: Record<string, string> = {
  green: "bg-success-soft text-success-fg ring-success-line",
  amber: "bg-warn-soft text-warn-fg ring-warn-line",
  red: "bg-danger-soft text-danger-fg ring-danger-line",
  blue: "bg-info-soft text-info-fg ring-info-line",
  violet: "bg-violet-soft text-violet-fg ring-violet-line",
  slate: "bg-surface-muted text-fg-soft ring-line-strong",
};

const STATUS_TONES: Record<string, keyof typeof BADGE_TONES> = {
  approved: "green",
  active: "green",
  completed: "green",
  sent: "green",
  linked: "green",
  pending: "amber",
  under_review: "amber",
  reading: "blue",
  in_progress: "blue",
  processing: "blue",
  retry_scheduled: "amber",
  revision_required: "violet",
  archived: "slate",
  todo: "slate",
  not_started: "slate",
  rejected: "red",
  suspended: "red",
  deleted: "red",
  failed: "red",
  overdue: "red",
  urgent: "red",
  high: "amber",
  medium: "blue",
  low: "slate",
};

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: keyof typeof BADGE_TONES }) {
  return (
    <span className={cx("inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", BADGE_TONES[tone])}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONES[status] ?? "slate"}>{humanize(status)}</Badge>;
}

export function Alert({ kind = "error", children }: { kind?: "error" | "success" | "info"; children: ReactNode }) {
  const styles = {
    error: "border-danger-line bg-danger-soft text-danger-fg",
    success: "border-success-line bg-success-soft text-success-fg",
    info: "border-info-line bg-info-soft text-info-fg",
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={cx("rounded-lg border px-4 py-3 text-sm", styles)}>
      {children}
    </div>
  );
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <Alert>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={onRetry}>
            Retry
          </Button>
        )}
      </div>
    </Alert>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-8 text-sm text-fg-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-ring" aria-hidden="true" />
      {label}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line-strong bg-surface-muted/40 px-4 py-10 text-center sm:px-6">
      <Inbox className="mx-auto mb-3 h-8 w-8 text-fg-subtle" aria-hidden="true" />
      <h3 className="text-sm font-semibold text-fg-soft">{title}</h3>
      {description && <p className="mx-auto mt-1 max-w-md text-sm text-fg-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div>
      {label && (
        <div className="mb-1 flex justify-between gap-2 text-xs text-fg-muted">
          <span>{label}</span>
          <span>{pct}%</span>
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-2 rounded-full bg-brand transition-[width]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ExternalLink({ href, children }: { href: string; children?: ReactNode }) {
  // Only http(s) links are rendered as clickable anchors.
  if (!/^https?:\/\//i.test(href)) return <span>{children ?? href}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="break-all text-link underline-offset-2 hover:underline">
      {children ?? href}
    </a>
  );
}


// Simple shimmering placeholder blocks for loading states.
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cx("skeleton h-4", className)} />;
}

export function SkeletonRows({ rows = 4, label = "Loading…" }: { rows?: number; label?: string }) {
  return (
    <div role="status" className="space-y-3 py-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={index % 2 ? "w-4/5" : "w-full"} />
      ))}
    </div>
  );
}
