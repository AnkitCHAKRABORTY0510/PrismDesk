import type { ReadingStatus } from "../services/researchService";

/** The three per-user reading states, in display order. */
export const READING_STATES: { id: ReadingStatus; label: string }[] = [
  { id: "not_started", label: "To read" },
  { id: "reading", label: "Reading" },
  { id: "completed", label: "Completed" },
];

export const readingLabel = (status: ReadingStatus | null | undefined) =>
  READING_STATES.find((state) => state.id === (status ?? "not_started"))?.label ?? "To read";
