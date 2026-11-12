// Calendar-day helpers. Days are plain "YYYY-MM-DD" strings in the
// viewer's local calendar; arithmetic is done at local noon so daylight
// saving changes never shift a day.

export type ISODate = string;

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function parseDay(day: ISODate): Date {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(year, month - 1, date, 12);
}

export function toDay(date: Date): ISODate {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function today(): ISODate {
  return toDay(new Date());
}

export function addDays(day: ISODate, amount: number): ISODate {
  const date = parseDay(day);
  date.setDate(date.getDate() + amount);
  return toDay(date);
}

// Same day of month in another month, clamped (Jan 31 + 1 month = Feb 28/29).
export function addMonths(day: ISODate, amount: number): ISODate {
  const date = parseDay(day);
  const target = new Date(date.getFullYear(), date.getMonth() + amount, 1, 12);
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  target.setDate(Math.min(date.getDate(), lastDay));
  return toDay(target);
}

export function startOfMonth(day: ISODate): ISODate {
  return `${day.slice(0, 7)}-01`;
}

export function endOfMonth(day: ISODate): ISODate {
  const date = parseDay(day);
  return toDay(new Date(date.getFullYear(), date.getMonth() + 1, 0, 12));
}

// Weeks start on Monday.
export function startOfWeek(day: ISODate): ISODate {
  const weekday = (parseDay(day).getDay() + 6) % 7;
  return addDays(day, -weekday);
}

export function weekDays(day: ISODate): ISODate[] {
  const start = startOfWeek(day);
  return Array.from({ length: 7 }, (_, index) => addDays(start, index));
}

// The weeks shown for a month: from the Monday on/before the 1st to the
// Sunday on/after the last day (4 to 6 rows).
export function monthWeeks(day: ISODate): ISODate[][] {
  const last = endOfMonth(day);
  const weeks: ISODate[][] = [];
  let cursor = startOfWeek(startOfMonth(day));
  while (cursor <= last) {
    weeks.push(weekDays(cursor));
    cursor = addDays(cursor, 7);
  }
  return weeks;
}

export function sameMonth(a: ISODate, b: ISODate): boolean {
  return a.slice(0, 7) === b.slice(0, 7);
}

export function monthLabel(day: ISODate): string {
  return parseDay(day).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

export function longDayLabel(day: ISODate): string {
  return parseDay(day).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export function wordCount(text: string): number {
  const words = text.trim().match(/\S+/g);
  return words ? words.length : 0;
}

// Consecutive days with writing, counting back from today (or from
// yesterday when today has nothing yet, so the streak is not "broken"
// before the day is over).
export function writingStreak(activeDays: Set<ISODate>, from: ISODate = today()): number {
  let cursor = activeDays.has(from) ? from : addDays(from, -1);
  let streak = 0;
  while (activeDays.has(cursor)) {
    streak += 1;
    cursor = addDays(cursor, -1);
  }
  return streak;
}

// 0 (nothing) to 4 (a lot) for the heat-map tint of a day.
export function activityLevel(entryCount: number, journalWords: number): 0 | 1 | 2 | 3 | 4 {
  const score = entryCount * 1.5 + (journalWords > 0 ? 1 : 0) + Math.min(journalWords / 150, 2);
  if (score <= 0) return 0;
  if (score < 1.5) return 1;
  if (score < 3) return 2;
  if (score < 4.5) return 3;
  return 4;
}
