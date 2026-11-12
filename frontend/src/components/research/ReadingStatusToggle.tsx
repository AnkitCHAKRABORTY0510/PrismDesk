import { useState, type MouseEvent } from "react";
import { BookOpen, Bookmark, CircleCheck } from "lucide-react";

import { useToast } from "../ui";
import { READING_STATES } from "../../lib/reading";
import { getErrorMessage } from "../../services/api";
import { setReadingStatus, type ReadingStatus } from "../../services/researchService";

const ICONS = { not_started: Bookmark, reading: BookOpen, completed: CircleCheck } as const;

// Segmented control: neutral track, the selected segment is raised with accent
// text (completed uses the success colour so "done" reads at a glance).
const PRESSED: Record<ReadingStatus, string> = {
  not_started: "bg-surface text-link shadow-[0_1px_2px_rgb(0_0_0/0.12)] ring-1 ring-line",
  reading: "bg-surface text-link shadow-[0_1px_2px_rgb(0_0_0/0.12)] ring-1 ring-line",
  completed: "bg-surface text-success-fg shadow-[0_1px_2px_rgb(0_0_0/0.12)] ring-1 ring-line",
};

interface Props {
  paperId: string;
  paperTitle?: string;
  /** The saved status (null means the user never set one: "To read"). */
  status: ReadingStatus | null;
  /** Called optimistically with the new status, and again with the old one if saving fails. */
  onChange?: (status: ReadingStatus) => void;
  /** Hide the text labels below the small breakpoint (icons stay). */
  compact?: boolean;
  className?: string;
}

/**
 * Three-segment To read / Reading / Completed switch. Each user sets their
 * own status; the change shows immediately and is saved in the background.
 */
export function ReadingStatusToggle({ paperId, paperTitle, status, onChange, compact = false, className = "" }: Props) {
  const { notify } = useToast();
  const saved = status ?? "not_started";
  // Optimistic value, only trusted while the saved status it was based on is unchanged.
  const [pending, setPending] = useState<{ base: ReadingStatus; value: ReadingStatus } | null>(null);
  const current = pending && pending.base === saved ? pending.value : saved;

  const choose = async (event: MouseEvent, next: ReadingStatus) => {
    event.stopPropagation();
    if (next === current) return;
    const previous = current;
    setPending({ base: saved, value: next });
    onChange?.(next);
    try {
      await setReadingStatus(paperId, next);
    } catch (err) {
      setPending({ base: saved, value: previous });
      onChange?.(previous);
      notify(getErrorMessage(err), "error");
    }
  };

  return (
    <div
      role="group"
      aria-label={paperTitle ? `My reading status for ${paperTitle}` : "My reading status"}
      className={`inline-flex shrink-0 items-center gap-0.5 rounded-md bg-surface-muted p-0.5 ring-1 ring-line ring-inset ${className}`}
      onClick={(event) => event.stopPropagation()}
    >
      {READING_STATES.map((state) => {
        const Icon = ICONS[state.id];
        const pressed = current === state.id;
        return (
          <button
            key={state.id}
            type="button"
            aria-pressed={pressed}
            title={state.label}
            onClick={(event) => void choose(event, state.id)}
            className={`inline-flex h-6 items-center gap-1 rounded-[5px] px-2 text-xs font-medium whitespace-nowrap transition-[color,background-color,box-shadow] duration-150 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring ${
              pressed ? PRESSED[state.id] : "text-fg-muted hover:text-fg"
            }`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
            <span className={compact ? "sr-only sm:not-sr-only" : ""}>{state.label}</span>
          </button>
        );
      })}
    </div>
  );
}
