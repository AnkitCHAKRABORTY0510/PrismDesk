type Tone = "green" | "amber" | "red" | "blue" | "violet" | "slate";

export const QUARTILE_TONES: Record<string, Tone> = { Q1: "green", Q2: "blue", Q3: "amber", Q4: "slate" };

const DAY_MS = 86_400_000;

export function deadlineTone(deadline: string, now: Date): Tone {
  const left = new Date(deadline).getTime() - now.getTime();
  if (left < 7 * DAY_MS) return "red";
  if (left < 30 * DAY_MS) return "amber";
  return "blue";
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "–";
  return value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
