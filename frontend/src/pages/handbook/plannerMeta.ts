import type { CSSProperties } from "react";
import { longDayLabel, today, type ISODate } from "../../lib/calendar";
import type { Pin, PinCategory, Reminder, Todo } from "../../services/handbookPlannerService";

// Pin categories and their theme-token colours (light and dark safe).
export const PIN_CATEGORIES: { id: PinCategory; label: string; dot: string; chip: string }[] = [
  { id: "deadline", label: "Deadline", dot: "bg-danger", chip: "border-danger-line bg-danger-soft text-danger-fg" },
  { id: "meeting", label: "Meeting", dot: "bg-info-fg", chip: "border-info-line bg-info-soft text-info-fg" },
  { id: "milestone", label: "Milestone", dot: "bg-success", chip: "border-success-line bg-success-soft text-success-fg" },
  { id: "idea", label: "Idea", dot: "bg-violet-fg", chip: "border-violet-line bg-violet-soft text-violet-fg" },
  { id: "other", label: "Other", dot: "bg-warn", chip: "border-warn-line bg-warn-soft text-warn-fg" },
];

export function pinMeta(category: string) {
  return PIN_CATEGORIES.find((item) => item.id === category) ?? PIN_CATEGORIES[PIN_CATEGORIES.length - 1];
}

// Heat-map tints for the writing activity of a day, level 0..4.
export const HEAT_CLASSES = ["", "bg-brand/10", "bg-brand/20", "bg-brand/30", "bg-brand/45"] as const;

export const ENTRY_FIELDS = [
  ["work_completed", "Work completed"],
  ["research_progress", "Research progress"],
  ["problems", "Problems encountered"],
  ["next_steps", "Next steps"],
  ["references", "References"],
] as const;

export const SUMMARY_FIELDS = [
  ["summary", "What I did"],
  ["challenges", "Challenges"],
  ["plan_next", "Plan for next day"],
] as const;

// Local storage is a convenience only; every access is guarded.
export function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Private mode or storage disabled: drafts are simply not kept.
  }
}

// What the calendar knows about one day.
export interface DayInfo {
  entries: number;
  journalWords: number;
  journalSnippet: string;
  // Notes shared with supervisors on this day (own note, or students' notes).
  sharedNotes: number;
  pins: Pin[];
  reminders: Reminder[];
  todos: Todo[];
}

export const EMPTY_DAY: DayInfo = { entries: 0, journalWords: 0, journalSnippet: "", sharedNotes: 0, pins: [], reminders: [], todos: [] };

export function openTodoCount(info: DayInfo) {
  return info.todos.filter((todo) => !todo.done).length;
}

export function activeReminders(info: DayInfo) {
  return info.reminders.filter((reminder) => !reminder.dismissed_at);
}

// Screen-reader summary of everything shown in a day cell.
export function describeDay(day: ISODate, info: DayInfo): string {
  const parts = [longDayLabel(day)];
  if (day === today()) parts.push("today");
  if (info.journalWords > 0) parts.push("journal written");
  if (info.entries > 0) parts.push(`${info.entries} project ${info.entries === 1 ? "entry" : "entries"}`);
  if (info.sharedNotes > 0) parts.push(info.sharedNotes === 1 ? "shared note" : `${info.sharedNotes} shared notes`);
  if (info.pins.length) parts.push(`pins: ${info.pins.map((pin) => pin.label).join(", ")}`);
  const reminders = activeReminders(info).length;
  if (reminders) parts.push(`${reminders} ${reminders === 1 ? "reminder" : "reminders"}`);
  const open = openTodoCount(info);
  if (open) parts.push(`${open} open ${open === 1 ? "to-do" : "to-dos"}`);
  return parts.join(", ");
}


export function draftKey(userId: string, day: ISODate) {
  return `prismdesk.handbook.draft.${userId}.${day}`;
}

// Ruled notebook lines drawn from theme tokens, so they follow light/dark.
// "local" attachment keeps the lines aligned with the text while scrolling.
export const RULED: CSSProperties = {
  backgroundImage: "repeating-linear-gradient(to bottom, transparent 0, transparent calc(2rem - 1px), var(--line) calc(2rem - 1px), var(--line) 2rem)",
  backgroundAttachment: "local",
  lineHeight: "2rem",
};


// Check each non-empty line of the references box; returns the clean URLs
// or a message naming the lines that are not http(s) links.
export function parseReferences(text: string): { urls: string[]; error: string } {
  const urls: string[] = [];
  const bad: number[] = [];
  text.split("\n").forEach((raw, index) => {
    const line = raw.trim();
    if (!line) return;
    try {
      const url = new URL(line);
      if (url.protocol !== "http:" && url.protocol !== "https:") throw new Error("not http");
      urls.push(line);
    } catch {
      bad.push(index + 1);
    }
  });
  if (bad.length) {
    return { urls, error: `${bad.length === 1 ? "Line" : "Lines"} ${bad.join(", ")} ${bad.length === 1 ? "is not a" : "are not"} valid link${bad.length === 1 ? "" : "s"} (start with https://).` };
  }
  if (urls.length > 20) return { urls, error: "Add at most 20 references." };
  return { urls, error: "" };
}
