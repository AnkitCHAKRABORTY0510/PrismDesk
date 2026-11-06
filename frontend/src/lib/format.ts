// All timestamps arrive from the API in UTC (ISO 8601) and are shown in
// the viewer's local timezone.

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  // Plain dates (YYYY-MM-DD) are calendar days, not instants.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString();
  }
  return new Date(value).toLocaleDateString();
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function countdown(target: string, now: Date = new Date()): string {
  const diff = new Date(target).getTime() - now.getTime();
  const overdue = diff < 0;
  const totalMinutes = Math.floor(Math.abs(diff) / 60000);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;

  const text = days > 0 ? `${days}d ${hours}h` : hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  return overdue ? `${text} overdue` : `${text} left`;
}

// Convert a <input type="datetime-local"> value to an ISO string with
// the browser's timezone offset applied.
export function localInputToIso(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

export function isoToLocalInput(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function todayLocal(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  return value.replace(/[_.]/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function splitList(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
