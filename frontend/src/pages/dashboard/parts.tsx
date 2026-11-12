import { useId, type ReactNode } from "react";
import { Link } from "react-router";

import type { MemberChip } from "../../services/dashboardService";
import { TONE_DOT, TONE_TEXT, initials, type Tone } from "./dashUtils";

/** Flat panel: 1px border, 10px radius, no shadow, quiet header. */
export function Panel({
  title,
  meta,
  action,
  className = "",
  bodyClassName = "p-4",
  children,
}: {
  title: string;
  meta?: ReactNode;
  action?: { to: string; label: string };
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section aria-labelledby={id} className={`dash-in min-w-0 rounded-[10px] border border-line bg-surface ${className}`}>
      <header className="flex min-h-11 items-center gap-2 border-b border-line px-4 py-2.5">
        <h2 id={id} className="text-[13px] font-semibold tracking-[-0.01em] text-fg">
          {title}
        </h2>
        {meta !== undefined && <span className="text-xs tabular-nums text-fg-subtle">{meta}</span>}
        {action && (
          <Link to={action.to} className="ml-auto rounded text-xs text-fg-muted transition-colors duration-150 hover:text-fg">
            {action.label} →
          </Link>
        )}
      </header>
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-fg-subtle">{children}</div>;
}

export interface Kpi {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  /** 0..1 thin progress bar under the figure. */
  ratio?: number;
  /** Small series for a sparkline (oldest first). */
  series?: number[];
  to?: string;
}

/** KPI figures without card boxes, divided by hairlines (2×2 on phones). */
export function KpiRow({ items }: { items: Kpi[] }) {
  return (
    <dl className={`dash-in grid grid-cols-2 border-y border-line ${items.length === 3 ? "lg:grid-cols-3" : "lg:grid-cols-4"}`}>
      {items.map((item, i) => {
        const body = (
          <>
            <dt>
              <Label>{item.label}</Label>
            </dt>
            <dd className="mt-1.5 flex items-end justify-between gap-3">
              <span className="text-[28px] leading-none font-semibold tracking-[-0.02em] tabular-nums text-fg">{item.value}</span>
              {item.series && item.series.length > 1 && <Sparkline values={item.series} />}
            </dd>
            {item.detail && <dd className="mt-1.5 text-xs text-fg-muted">{item.detail}</dd>}
            {item.ratio !== undefined && (
              <dd className="mt-2.5">
                <Progress ratio={item.ratio} />
              </dd>
            )}
          </>
        );
        const cell = `block min-w-0 px-4 py-4 ${i % 2 === 1 ? "border-l border-line" : ""} ${i >= 2 ? "border-t border-line lg:border-t-0" : ""} ${i === 2 ? "lg:border-l" : ""}`;
        return item.to ? (
          <div key={item.label} className={cell}>
            <Link to={item.to} className="-m-2 block rounded-md p-2 transition-colors duration-150 hover:bg-surface-muted">
              {body}
            </Link>
          </div>
        ) : (
          <div key={item.label} className={cell}>
            {body}
          </div>
        );
      })}
    </dl>
  );
}

/** Accent line, faint area, emphasised last point. Decorative; the figure carries the value. */
export function Sparkline({ values, width = 84, height = 26 }: { values: number[]; width?: number; height?: number }) {
  const max = Math.max(1, ...values);
  const step = width / (values.length - 1);
  const points = values.map((v, i) => [i * step, height - 3 - (v / max) * (height - 6)] as const);
  const line = points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const [lx, ly] = points[points.length - 1];
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} aria-hidden="true" className="shrink-0 overflow-visible">
      <path d={`${line} L${width} ${height} L0 ${height} Z`} fill="var(--primary)" opacity="0.08" />
      <path d={line} fill="none" stroke="var(--primary)" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="2.5" fill="var(--primary)" stroke="var(--surface)" strokeWidth="1.5" />
    </svg>
  );
}

export function Progress({ ratio, color = "var(--primary)", className = "h-1" }: { ratio: number; color?: string; className?: string }) {
  const pct = Math.round(Math.min(1, Math.max(0, ratio)) * 100);
  return (
    <div className={`w-full overflow-hidden rounded-full bg-track ${className}`} aria-hidden="true">
      <div className="dash-bar h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export interface Segment {
  key: string;
  label: string;
  value: number;
  color: string;
  to?: string;
}

/** One stacked horizontal bar with a legend of counts; segments and legend items can link. */
export function StackedBar({ segments, label, legend = true, className = "h-2" }: { segments: Segment[]; label: string; legend?: boolean; className?: string }) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  return (
    <div className="min-w-0">
      <div
        role="img"
        aria-label={`${label}: ${segments.map((s) => `${s.label} ${s.value}`).join(", ")}`}
        className={`flex w-full gap-[2px] overflow-hidden rounded-full bg-track ${className}`}
      >
        {total > 0 &&
          segments
            .filter((s) => s.value > 0)
            .map((s) =>
              s.to ? (
                <Link
                  key={s.key}
                  to={s.to}
                  tabIndex={-1}
                  aria-hidden="true"
                  title={`${s.label}: ${s.value}`}
                  className="dash-bar h-full transition-opacity duration-150 hover:opacity-80"
                  style={{ flex: `${s.value} 1 0%`, background: s.color }}
                />
              ) : (
                <span key={s.key} title={`${s.label}: ${s.value}`} className="dash-bar h-full" style={{ flex: `${s.value} 1 0%`, background: s.color }} />
              )
            )}
      </div>
      {legend && (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-fg-muted">
          {segments.map((s) => {
            const content = (
              <>
                <span className="h-2 w-2 shrink-0 rounded-[2px]" style={{ background: s.color }} aria-hidden="true" />
                {s.label}
                <span className="font-medium tabular-nums text-fg">{s.value}</span>
              </>
            );
            return (
              <li key={s.key}>
                {s.to ? (
                  <Link to={s.to} className="inline-flex items-center gap-1.5 rounded transition-colors duration-150 hover:text-fg">
                    {content}
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1.5">{content}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function Avatar({ name, title, size = "h-6 w-6 text-[10px]" }: { name: string; title?: string; size?: string }) {
  return (
    <span
      title={title ?? name}
      className={`grid shrink-0 place-items-center rounded-full bg-surface-muted font-semibold text-fg-soft ring-1 ring-line ${size}`}
    >
      {initials(name)}
    </span>
  );
}

export function AvatarStack({ members, total }: { members: MemberChip[]; total: number }) {
  const shown = members.slice(0, 4);
  const extra = Math.max(0, total - shown.length);
  return (
    <div className="flex items-center gap-1" aria-label={`${total} member${total === 1 ? "" : "s"}`}>
      {shown.map((m) => (
        <span key={m.user_id} className="rounded-full">
          <Avatar name={m.full_name} title={`${m.full_name} (@${m.username})`} />
        </span>
      ))}
      {extra > 0 && (
        <span className="grid h-6 min-w-6 place-items-center rounded-full px-1 text-[10px] font-medium tabular-nums text-fg-muted">
          +{extra}
        </span>
      )}
    </div>
  );
}

/** Small status pill: semantic dot + text (colour is never the only signal). */
export function Pill({ tone, children, to }: { tone: Tone; children: ReactNode; to?: string }) {
  const cls = `inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium ${TONE_TEXT[tone]} ${tone === "neutral" ? "text-fg-soft" : ""}`;
  const body = (
    <>
      <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]}`} aria-hidden="true" />
      {children}
    </>
  );
  return to ? (
    <Link to={to} className={`${cls} transition-colors duration-150 hover:border-line-strong`}>
      {body}
    </Link>
  ) : (
    <span className={cls}>{body}</span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="px-1 py-6 text-center text-sm text-fg-muted">{children}</p>;
}
