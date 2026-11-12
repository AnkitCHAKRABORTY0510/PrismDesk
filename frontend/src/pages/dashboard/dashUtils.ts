// Pure helpers for the dashboard (kept apart from components for fast refresh).

export type Tone = "danger" | "warn" | "success" | "accent" | "neutral";

const DAY = 86_400_000;

/** Whole calendar days from now until ``iso`` (0 = today, negative = past). */
export function daysUntil(iso: string, now: Date = new Date()): number {
  const target = new Date(iso);
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const end = new Date(target.getFullYear(), target.getMonth(), target.getDate()).getTime();
  return Math.round((end - start) / DAY);
}

export function daysSince(iso: string, now: Date = new Date()): number {
  return Math.max(0, -daysUntil(iso, now));
}

/** "today", "tomorrow", "in 4 days", "2 days ago". */
export function relativeDay(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  return days > 0 ? `in ${days} days` : `${-days} days ago`;
}

/** Deadline urgency: only the near ones get a semantic colour. */
export function urgencyTone(days: number): Tone {
  if (days <= 2) return "danger";
  if (days <= 7) return "warn";
  return "neutral";
}

export const TONE_TEXT: Record<Tone, string> = {
  danger: "text-danger-fg",
  warn: "text-warn-fg",
  success: "text-success-fg",
  accent: "text-link",
  neutral: "text-fg-muted",
};

export const TONE_DOT: Record<Tone, string> = {
  danger: "bg-danger",
  warn: "bg-warn",
  success: "bg-success",
  accent: "bg-brand",
  neutral: "bg-line-strong",
};

/** Accent at a given strength over the neutral track (for ramps and heatmaps). */
export const accentMix = (percent: number) => `color-mix(in srgb, var(--primary) ${percent}%, var(--track))`;

/** Local calendar day as YYYY-MM-DD. */
export function isoDay(date: Date): string {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

export function greeting(now: Date = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

/** Official assignment stages: neutral for waiting, accent for moving, semantic for problems/done. */
export const STAGES: { key: string; label: string; color: string }[] = [
  { key: "todo", label: "To do", color: "var(--line-strong)" },
  { key: "in_progress", label: "In progress", color: "var(--primary)" },
  { key: "under_review", label: "Submitted", color: accentMix(45) },
  { key: "revision_required", label: "Needs revision", color: "var(--warn)" },
  { key: "completed", label: "Approved", color: "var(--success)" },
];

export const READING_COLORS: Record<string, string> = {
  not_started: "var(--line-strong)",
  reading: "var(--primary)",
  completed: "var(--success)",
};
