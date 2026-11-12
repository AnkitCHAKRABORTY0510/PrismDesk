import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { ChevronLeft, ChevronRight, ExternalLink as ExternalIcon, Lock, MessageSquare, PenLine, Plus, Users, X } from "lucide-react";

import { Badge, Button, ErrorMessage, Loading, Tabs } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { addDays, parseDay, today as todayDay, type ISODate } from "../../lib/calendar";
import { listEntries, listSharedNotes, listSummaries, type DailySummary, type HandbookEntry, type SharedNote } from "../../services/handbookService";
import { getPlanner } from "../../services/handbookPlannerService";
import EntryFormModal from "./EntryFormModal";
import { JournalEditor } from "./JournalEditor";
import { PinPanel, ReminderPanel, TodoPanel } from "./PlannerPanels";
import { EMPTY_DAY, activeReminders } from "./plannerMeta";
import { SharedNoteEditor, SupervisorSharedNotes } from "./SharedNotes";

type Section = "journal" | "todos" | "reminders" | "pins";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function isTyping(target: EventTarget | null) {
  const element = target as HTMLElement | null;
  return !!element && (element.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName));
}

// A notebook page for one calendar day: the private journal, that day's
// project entries, and the personal planner (to-dos, reminders, pins).
export function DayPage({
  day,
  userId,
  canWrite,
  initialSection = "journal",
  onNavigate,
  onClose,
  onChanged,
}: {
  day: ISODate;
  userId: string;
  canWrite: boolean;
  initialSection?: Section;
  onNavigate: (day: ISODate) => void;
  onClose: () => void;
  onChanged: () => void;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [section, setSection] = useState<Section>(initialSection);
  // Unsaved text in either the private journal or the shared note.
  const [privateDirty, setPrivateDirty] = useState(false);
  const [sharedDirty, setSharedDirty] = useState(false);
  const dirty = privateDirty || sharedDirty;
  const [pending, setPending] = useState<{ kind: "close" } | { kind: "go"; day: ISODate } | null>(null);
  const [direction, setDirection] = useState<"next" | "prev" | "open">("open");
  const [childOpen, setChildOpen] = useState(false);
  const [entryForm, setEntryForm] = useState<HandbookEntry | "new" | null>(null);

  const today = todayDay();
  const isFuture = day > today;
  const isToday = day === today;

  const summary = useAsync(
    async () => (canWrite ? ((await listSummaries({ date_from: day, date_to: day, page_size: 1 })).items[0] ?? null) : null),
    [day, canWrite]
  );
  const entries = useAsync(() => listEntries({ date_from: day, date_to: day, page_size: 50 }), [day]);
  const sharedNotes = useAsync(() => listSharedNotes({ date_from: day, date_to: day, page_size: 50 }), [day]);
  const ownShared = sharedNotes.data?.items.find((note) => note.student.id === userId) ?? null;
  const replaceShared = (note: SharedNote) => {
    if (!sharedNotes.data) return;
    const others = sharedNotes.data.items.filter((item) => item.id !== note.id);
    sharedNotes.setData({ ...sharedNotes.data, items: [...others, note], total: others.length + 1 });
    onChanged();
  };
  const planner = useAsync(() => getPlanner(day, day), [day]);

  const reloadPlanner = useCallback(() => {
    void planner.reload();
    onChanged();
  }, [planner, onChanged]);

  // Leaving with unsaved journal text asks first.
  const request = (next: { kind: "close" } | { kind: "go"; day: ISODate }) => {
    if (dirty) {
      setPending(next);
      return;
    }
    perform(next);
  };
  const perform = (next: { kind: "close" } | { kind: "go"; day: ISODate }) => {
    setPending(null);
    setPrivateDirty(false);
    setSharedDirty(false);
    if (next.kind === "close") onClose();
    else {
      setDirection(next.day > day ? "next" : "prev");
      onNavigate(next.day);
    }
  };

  const requestRef = useRef(request);
  const childOpenRef = useRef(childOpen);
  useEffect(() => {
    requestRef.current = request;
    childOpenRef.current = childOpen;
  });

  // Focus, Escape, Tab trapping and arrow-key paging, ignoring keys meant
  // for a dialog opened on top of this page.
  useEffect(() => {
    const dialog = dialogRef.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialog?.focus();
    const handler = (event: KeyboardEvent) => {
      if (!dialog || childOpenRef.current) return;
      const top = (document.activeElement as HTMLElement | null)?.closest('[role="dialog"]');
      if (top && top !== dialog) return;
      if (event.key === "Escape") {
        event.preventDefault();
        requestRef.current({ kind: "close" });
      } else if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !isTyping(event.target) && (event.target as HTMLElement)?.getAttribute("role") !== "tab") {
        event.preventDefault();
        requestRef.current({ kind: "go", day: addDays(dialog.dataset.day ?? "", event.key === "ArrowLeft" ? -1 : 1) });
      } else if (event.key === "Tab") {
        const focusable = dialog.querySelectorAll<HTMLElement>(FOCUSABLE);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", handler);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = overflow;
      previouslyFocused?.focus?.();
    };
  }, []);

  const todos = planner.data?.todos ?? [];
  const reminders = planner.data?.reminders ?? [];
  const pins = planner.data?.pins ?? [];
  const openTodos = todos.filter((todo) => !todo.done).length;
  const remindersActive = activeReminders({ ...EMPTY_DAY, pins, reminders, todos }).length;

  const turn =
    direction === "next" ? "slide-in-from-right-8" : direction === "prev" ? "slide-in-from-left-8" : "slide-in-from-bottom-4 sm:zoom-in-95";

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-stretch justify-center bg-[var(--overlay)] backdrop-blur-[2px] sm:items-start sm:p-4 sm:pt-10"
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) request({ kind: "close" });
        }}
      >
        <div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          data-day={day}
          tabIndex={-1}
          className="relative flex h-full w-full flex-col overflow-hidden bg-surface-raised shadow-pop outline-none sm:h-auto sm:max-h-[calc(100svh-5rem)] sm:max-w-3xl sm:rounded-2xl sm:border sm:border-line"
        >
          {/* Notebook binding along the top edge. */}
          <div aria-hidden="true" className="h-1.5 shrink-0 bg-rainbow opacity-80" />
          <header className="flex shrink-0 items-start gap-2 border-b border-line px-4 pb-3 pt-3 sm:px-6 sm:pt-4">
            <button
              type="button"
              aria-label="Previous day"
              title="Previous day (←)"
              onClick={() => request({ kind: "go", day: addDays(day, -1) })}
              className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-fg-muted transition-colors hover:bg-surface-muted hover:text-fg"
            >
              <ChevronLeft className="h-5 w-5" aria-hidden="true" />
            </button>
            <div className="min-w-0 flex-1 text-center">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-fg-subtle">
                Research handbook · {parseDay(day).toLocaleDateString(undefined, { weekday: "long" })}
              </p>
              <h2 id={titleId} className="font-serif text-xl font-semibold text-fg sm:text-2xl">
                {parseDay(day).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}
              </h2>
              <div className="mt-1 flex justify-center gap-2">
                {isToday && <Badge tone="blue">Today</Badge>}
                {isFuture && <Badge tone="violet">Planning ahead</Badge>}
              </div>
            </div>
            <button
              type="button"
              aria-label="Next day"
              title="Next day (→)"
              onClick={() => request({ kind: "go", day: addDays(day, 1) })}
              className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-fg-muted transition-colors hover:bg-surface-muted hover:text-fg"
            >
              <ChevronRight className="h-5 w-5" aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Close day page"
              onClick={() => request({ kind: "close" })}
              className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-muted hover:text-fg"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </header>

          {pending && (
            <div role="alertdialog" aria-label="Unsaved changes" className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-warn-line bg-warn-soft px-4 py-2.5 text-sm text-warn-fg sm:px-6">
              <span>Your journal has unsaved changes. A draft stays on this device.</span>
              <span className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => setPending(null)} autoFocus>Keep editing</Button>
                <Button size="sm" variant="ghost" onClick={() => perform(pending)}>{pending.kind === "close" ? "Close anyway" : "Leave anyway"}</Button>
              </span>
            </div>
          )}

          <div className="shrink-0 px-4 pt-2 sm:px-6">
            <Tabs
              tabs={[
                { id: "journal" as Section, label: canWrite ? "Journal" : "Entries" },
                { id: "todos" as Section, label: openTodos ? `To-dos (${openTodos})` : "To-dos" },
                { id: "reminders" as Section, label: remindersActive ? `Reminders (${remindersActive})` : "Reminders" },
                { id: "pins" as Section, label: pins.length ? `Pins (${pins.length})` : "Pins" },
              ]}
              active={section}
              onChange={setSection}
            />
          </div>

          <div key={day} className={`min-h-0 flex-1 overflow-y-auto px-4 py-5 animate-in fade-in-0 duration-300 sm:px-6 ${turn}`}>
            {section === "journal" && (
              <div className="space-y-8">
                {canWrite &&
                  (isFuture ? (
                    <FutureNotice onPick={setSection} />
                  ) : summary.loading ? (
                    <Loading label="Opening the page…" />
                  ) : summary.error ? (
                    <ErrorMessage message={summary.error} onRetry={summary.reload} />
                  ) : (
                    <>
                      <section aria-labelledby="private-notes-heading" className="space-y-3">
                        <SectionTitle id="private-notes-heading" icon={<Lock className="h-4 w-4 text-fg-muted" aria-hidden="true" />} title="Private notes" hint="Only you can read these." />
                        <JournalEditor
                          key={`${day}-${summary.data?.id ?? "new"}`}
                          day={day}
                          userId={userId}
                          summary={summary.data}
                          onDirtyChange={setPrivateDirty}
                          onOpenChild={setChildOpen}
                          onSaved={(saved: DailySummary) => {
                            summary.setData(saved);
                            onChanged();
                          }}
                        />
                      </section>
                      <section aria-labelledby="shared-note-heading" className="space-y-3">
                        <SectionTitle id="shared-note-heading" icon={<Users className="h-4 w-4 text-info-fg" aria-hidden="true" />} title="Shared with supervisor" hint="Your project supervisors can read this and reply." />
                        {sharedNotes.loading ? (
                          <Loading />
                        ) : sharedNotes.error ? (
                          <ErrorMessage message={sharedNotes.error} onRetry={sharedNotes.reload} />
                        ) : (
                          <SharedNoteEditor
                            key={`${day}-${ownShared?.id ?? "new"}`}
                            day={day}
                            userId={userId}
                            note={ownShared}
                            onDirtyChange={setSharedDirty}
                            onOpenChild={setChildOpen}
                            onSaved={replaceShared}
                          />
                        )}
                      </section>
                    </>
                  ))}
                {!canWrite && (
                  <>
                    <p className="flex items-center gap-2 text-sm text-fg-muted">
                      <Lock className="h-4 w-4 shrink-0" aria-hidden="true" />
                      Students' private notes stay private. You see what they shared with you and their project entries.
                    </p>
                    {sharedNotes.loading && !sharedNotes.data ? (
                      <Loading />
                    ) : sharedNotes.error ? (
                      <ErrorMessage message={sharedNotes.error} onRetry={sharedNotes.reload} />
                    ) : (
                      <SupervisorSharedNotes notes={sharedNotes.data?.items ?? []} onChanged={replaceShared} />
                    )}
                  </>
                )}
                <EntriesSection
                  entries={entries.data?.items ?? []}
                  loading={entries.loading && !entries.data}
                  error={entries.error}
                  onRetry={entries.reload}
                  canAdd={canWrite && !isFuture}
                  isFuture={isFuture}
                  canWrite={canWrite}
                  onAdd={() => {
                    setEntryForm("new");
                    setChildOpen(true);
                  }}
                  onEdit={(entry) => {
                    setEntryForm(entry);
                    setChildOpen(true);
                  }}
                />
              </div>
            )}
            {section !== "journal" && planner.loading && !planner.data && <Loading />}
            {section !== "journal" && <ErrorMessage message={planner.error} onRetry={planner.reload} />}
            {section === "todos" && planner.data && <TodoPanel day={day} todos={todos} onChanged={reloadPlanner} />}
            {section === "reminders" && planner.data && <ReminderPanel day={day} reminders={reminders} onChanged={reloadPlanner} />}
            {section === "pins" && planner.data && <PinPanel day={day} pins={pins} onChanged={reloadPlanner} />}
          </div>
        </div>
      </div>

      {entryForm && (
        <EntryFormModal
          open
          entry={entryForm === "new" ? null : entryForm}
          defaultDate={day}
          onClose={() => {
            setEntryForm(null);
            setChildOpen(false);
          }}
          onSaved={() => {
            setEntryForm(null);
            setChildOpen(false);
            void entries.reload();
            onChanged();
          }}
        />
      )}
    </>
  );
}

function FutureNotice({ onPick }: { onPick: (section: Section) => void }) {
  return (
    <div className="rounded-xl border border-dashed border-violet-line bg-violet-soft px-5 py-6 text-center">
      <PenLine className="mx-auto mb-2 h-6 w-6 text-violet-fg" aria-hidden="true" />
      <p className="font-serif text-lg text-fg">This page is still blank.</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-fg-muted">
        Journals and project entries can only be written for today or earlier. You can already plan this day:
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <Button size="sm" variant="secondary" onClick={() => onPick("todos")}>Add to-dos</Button>
        <Button size="sm" variant="secondary" onClick={() => onPick("reminders")}>Set a reminder</Button>
        <Button size="sm" variant="secondary" onClick={() => onPick("pins")}>Pin it</Button>
      </div>
    </div>
  );
}

function EntriesSection({
  entries,
  loading,
  error,
  onRetry,
  canAdd,
  canWrite,
  isFuture,
  onAdd,
  onEdit,
}: {
  entries: HandbookEntry[];
  loading: boolean;
  error: string;
  onRetry: () => void;
  canAdd: boolean;
  canWrite: boolean;
  isFuture: boolean;
  onAdd: () => void;
  onEdit: (entry: HandbookEntry) => void;
}) {
  return (
    <section aria-labelledby="day-entries-heading" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="day-entries-heading" className="text-sm font-semibold text-fg">Project entries</h3>
        {canAdd && (
          <Button size="sm" variant="secondary" onClick={onAdd}>
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            Add project entry
          </Button>
        )}
      </div>
      <ErrorMessage message={error} onRetry={onRetry} />
      {loading ? (
        <Loading />
      ) : entries.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line-strong px-4 py-4 text-center text-sm text-fg-muted">
          {isFuture ? "No entries: this day hasn't happened yet." : canWrite ? "No project entries for this day." : "None of your students wrote an entry on this day."}
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {entries.map((entry) => (
            <EntryCard key={entry.id} entry={entry} showStudent={!canWrite || !entry.can_edit} onEdit={() => onEdit(entry)} />
          ))}
        </ul>
      )}
    </section>
  );
}

function EntryCard({ entry, showStudent, onEdit }: { entry: HandbookEntry; showStudent: boolean; onEdit: () => void }) {
  const preview = entry.work_completed || entry.research_progress || entry.next_steps || entry.problems;
  return (
    <li className="flex flex-col rounded-xl border border-line bg-surface p-4 shadow-card">
      <div className="mb-1 flex items-start justify-between gap-2">
        <p className="min-w-0 truncate font-medium text-fg">{entry.project_title ?? "Project"}</p>
        <span className="shrink-0 text-xs text-fg-subtle">v{entry.version}</span>
      </div>
      {showStudent && <p className="mb-1 text-xs text-fg-muted">{entry.student.full_name}</p>}
      <p className="line-clamp-3 flex-1 text-sm text-fg-soft">{preview}</p>
      <div className="mt-3 flex items-center gap-2 text-xs">
        <span className="inline-flex items-center gap-1 text-fg-muted">
          <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
          {entry.comment_count}
          <span className="sr-only">comments</span>
        </span>
        <span className="flex-1" />
        {entry.can_edit && (
          <Button size="sm" variant="ghost" onClick={onEdit} aria-label={`Edit entry for ${entry.project_title ?? "project"}`}>
            Edit
          </Button>
        )}
        <Link
          to={`/handbook/entries/${entry.id}`}
          className="inline-flex h-8 items-center gap-1 rounded-lg px-2 font-medium text-link hover:bg-surface-muted"
          aria-label={`Open full entry for ${entry.project_title ?? "project"}: versions and comments`}
        >
          Open
          <ExternalIcon className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
    </li>
  );
}

function SectionTitle({ id, icon, title, hint }: { id: string; icon: ReactNode; title: string; hint: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
      <h3 id={id} className="flex items-center gap-2 text-sm font-semibold text-fg">
        {icon}
        {title}
      </h3>
      <span className="text-xs text-fg-muted">{hint}</span>
    </div>
  );
}
