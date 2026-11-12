import { useEffect, useRef, type KeyboardEvent, type ReactNode } from "react";
import { Bell, CalendarDays, ChevronLeft, ChevronRight, ListTodo, NotebookPen, Rows3, Users } from "lucide-react";

import {
  WEEKDAYS,
  activityLevel,
  addDays,
  addMonths,
  monthLabel,
  monthWeeks,
  parseDay,
  sameMonth,
  startOfMonth,
  startOfWeek,
  today as todayDay,
  weekDays,
  type ISODate,
} from "../../lib/calendar";
import { EMPTY_DAY, HEAT_CLASSES, PIN_CATEGORIES, activeReminders, describeDay, openTodoCount, pinMeta, type DayInfo } from "./plannerMeta";

export type CalendarMode = "month" | "week";

const YEAR_SPAN = 6;

export function CalendarView({
  focused,
  onFocus,
  onOpen,
  mode,
  onModeChange,
  days,
  loading = false,
}: {
  focused: ISODate;
  onFocus: (day: ISODate) => void;
  onOpen: (day: ISODate) => void;
  mode: CalendarMode;
  onModeChange: (mode: CalendarMode) => void;
  days: Map<ISODate, DayInfo>;
  loading?: boolean;
}) {
  const gridRef = useRef<HTMLDivElement>(null);
  const keyboardMove = useRef(false);
  const today = todayDay();
  const weeks = mode === "month" ? monthWeeks(focused) : [weekDays(focused)];
  const thisYear = parseDay(today).getFullYear();
  const focusedDate = parseDay(focused);

  // Keep DOM focus on the focused day after keyboard navigation (including
  // when it moves into another month and the grid re-renders).
  useEffect(() => {
    if (!keyboardMove.current) return;
    keyboardMove.current = false;
    gridRef.current?.querySelector<HTMLButtonElement>(`[data-day="${focused}"]`)?.focus();
  }, [focused, mode]);

  const step = (amount: number) => onFocus(mode === "month" ? addMonths(focused, amount) : addDays(focused, amount * 7));

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const moves: Record<string, () => ISODate> = {
      ArrowLeft: () => addDays(focused, -1),
      ArrowRight: () => addDays(focused, 1),
      ArrowUp: () => addDays(focused, -7),
      ArrowDown: () => addDays(focused, 7),
      Home: () => startOfWeek(focused),
      End: () => addDays(startOfWeek(focused), 6),
      PageUp: () => addMonths(focused, -1),
      PageDown: () => addMonths(focused, 1),
    };
    if (moves[event.key]) {
      event.preventDefault();
      keyboardMove.current = true;
      onFocus(moves[event.key]());
    } else if (event.key === "t" || event.key === "T") {
      event.preventDefault();
      keyboardMove.current = true;
      onFocus(today);
    }
  };

  const heading = mode === "month" ? monthLabel(focused) : `Week of ${parseDay(startOfWeek(focused)).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <IconButton label={mode === "month" ? "Previous month" : "Previous week"} onClick={() => step(-1)}>
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </IconButton>
          <IconButton label={mode === "month" ? "Next month" : "Next week"} onClick={() => step(1)}>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </IconButton>
          <button
            type="button"
            onClick={() => onFocus(today)}
            className="ml-1 h-9 rounded-lg border border-line-strong bg-surface px-3 text-sm font-medium text-fg-soft transition-colors hover:bg-surface-muted hover:text-fg"
          >
            Today
          </button>
          <h2 className="ml-3 font-serif text-lg font-semibold text-fg sm:text-xl" aria-live="polite">
            {heading}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="hb-jump-month">Jump to month</label>
          <select
            id="hb-jump-month"
            value={focusedDate.getMonth()}
            onChange={(e) => onFocus(addMonths(startOfMonth(focused), Number(e.target.value) - focusedDate.getMonth()))}
            className="h-9 rounded-lg border border-line-strong bg-surface px-2 text-sm text-fg"
          >
            {Array.from({ length: 12 }, (_, month) => (
              <option key={month} value={month}>
                {new Date(2000, month, 1).toLocaleDateString(undefined, { month: "long" })}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="hb-jump-year">Jump to year</label>
          <select
            id="hb-jump-year"
            value={focusedDate.getFullYear()}
            onChange={(e) => onFocus(addMonths(startOfMonth(focused), (Number(e.target.value) - focusedDate.getFullYear()) * 12))}
            className="h-9 rounded-lg border border-line-strong bg-surface px-2 text-sm text-fg"
          >
            {Array.from({ length: YEAR_SPAN * 2 + 1 }, (_, index) => thisYear - YEAR_SPAN + index).map((year) => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
          <div role="group" aria-label="Calendar view" className="flex rounded-lg border border-line-strong bg-surface p-0.5">
            {(["month", "week"] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={mode === option}
                onClick={() => onModeChange(option)}
                className={`inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors ${
                  mode === option ? "bg-brand text-brand-fg shadow-sm" : "text-fg-muted hover:text-fg"
                }`}
              >
                {option === "month" ? <CalendarDays className="h-4 w-4" aria-hidden="true" /> : <Rows3 className="h-4 w-4" aria-hidden="true" />}
                {option === "month" ? "Month" : "Week"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div
        ref={gridRef}
        role="grid"
        aria-label={`${heading}. Arrow keys move between days, Enter opens a day, T jumps to today.`}
        aria-busy={loading}
        onKeyDown={onKeyDown}
        className="overflow-hidden rounded-xl border border-line"
      >
        <div role="row" className="grid grid-cols-7 border-b border-line bg-surface-muted">
          {WEEKDAYS.map((name) => (
            <div key={name} role="columnheader" className="px-1 py-2 text-center text-xs font-semibold uppercase tracking-wide text-fg-muted sm:px-2 sm:text-left">
              <span aria-hidden="true" className="sm:hidden">{name[0]}</span>
              <span className="max-sm:sr-only">{name}</span>
            </div>
          ))}
        </div>
        <div key={`${mode}-${weeks[0][0]}`} className="animate-in fade-in-0 duration-300">
          {weeks.map((week) => (
            <div key={week[0]} role="row" className="grid grid-cols-7 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-line">
              {week.map((day) => (
                <DayCell
                  key={day}
                  day={day}
                  info={days.get(day) ?? EMPTY_DAY}
                  mode={mode}
                  inMonth={mode === "week" || sameMonth(day, focused)}
                  isToday={day === today}
                  isFuture={day > today}
                  isFocused={day === focused}
                  onFocus={() => onFocus(day)}
                  onOpen={() => onOpen(day)}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <Legend />

      <Agenda days={weekDays(focused)} info={days} onOpen={onOpen} hidden={mode === "week"} />
    </div>
  );
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line-strong bg-surface text-fg-soft transition-colors hover:bg-surface-muted hover:text-fg"
    >
      {children}
    </button>
  );
}

function DayCell({
  day,
  info,
  mode,
  inMonth,
  isToday,
  isFuture,
  isFocused,
  onFocus,
  onOpen,
}: {
  day: ISODate;
  info: DayInfo;
  mode: CalendarMode;
  inMonth: boolean;
  isToday: boolean;
  isFuture: boolean;
  isFocused: boolean;
  onFocus: () => void;
  onOpen: () => void;
}) {
  const level = activityLevel(info.entries, info.journalWords);
  const open = openTodoCount(info);
  const reminders = activeReminders(info);
  const dayNumber = Number(day.slice(8));
  const week = mode === "week";

  return (
    <div role="gridcell" aria-selected={isFocused} className="min-w-0 [&:not(:last-child)]:border-r [&:not(:last-child)]:border-line">
      <button
        type="button"
        data-day={day}
        tabIndex={isFocused ? 0 : -1}
        aria-label={describeDay(day, info)}
        aria-current={isToday ? "date" : undefined}
        onClick={() => {
          onFocus();
          onOpen();
        }}
        onFocus={() => !isFocused && onFocus()}
        className={`group relative flex w-full flex-col items-stretch gap-1 p-1 text-left transition-colors focus-visible:z-10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring sm:p-2 ${
          week ? "min-h-40 md:min-h-72" : "h-14 sm:h-24 lg:h-28"
        } ${inMonth ? "bg-surface hover:bg-surface-muted" : "bg-surface-muted/50 hover:bg-surface-muted"} ${
          isFocused ? "ring-2 ring-inset ring-ring/60" : ""
        }`}
      >
        {/* Heat-map tint of writing activity. */}
        {level > 0 && <span aria-hidden="true" className={`pointer-events-none absolute inset-0 ${HEAT_CLASSES[level]}`} />}
        <span className="relative flex items-center justify-between gap-1">
          <span
            className={`inline-flex h-6 min-w-6 items-center justify-center whitespace-nowrap rounded-full px-1.5 text-xs font-semibold tabular-nums sm:h-7 sm:min-w-7 sm:text-sm ${
              isToday
                ? "bg-brand text-brand-fg shadow-sm"
                : !inMonth
                  ? "text-fg-subtle"
                  : isFuture
                    ? "text-fg-muted"
                    : "text-fg"
            }`}
          >
            {week ? parseDay(day).toLocaleDateString(undefined, { weekday: "short", day: "numeric" }) : dayNumber}
          </span>
          <span className="flex items-center gap-1 text-fg-muted">
            {reminders.length > 0 && <Bell className="h-3 w-3 text-warn-fg sm:h-3.5 sm:w-3.5" aria-hidden="true" />}
            {info.sharedNotes > 0 && <Users className="h-3 w-3 text-info-fg sm:h-3.5 sm:w-3.5" aria-hidden="true" />}
            {(info.journalWords > 0 || info.entries > 0) && <NotebookPen className="h-3 w-3 text-link sm:h-3.5 sm:w-3.5" aria-hidden="true" />}
          </span>
        </span>

        {week ? (
          <WeekDetails info={info} />
        ) : (
          <span className="relative mt-auto flex flex-wrap items-center gap-1">
            {info.pins.slice(0, 3).map((pin) => (
              <span key={pin.id} aria-hidden="true" title={pin.label} className={`h-1.5 w-1.5 rounded-full sm:h-2 sm:w-2 ${pinMeta(pin.category).dot}`} />
            ))}
            {info.pins.length > 3 && <span aria-hidden="true" className="text-[10px] leading-none text-fg-muted">+{info.pins.length - 3}</span>}
            {info.pins[0] && (
              <span aria-hidden="true" className="hidden min-w-0 flex-1 truncate text-[11px] text-fg-soft lg:inline">{info.pins[0].label}</span>
            )}
            {open > 0 && (
              <span aria-hidden="true" className="ml-auto hidden items-center gap-0.5 rounded bg-surface-muted px-1 text-[10px] font-medium text-fg-muted ring-1 ring-line sm:inline-flex">
                <ListTodo className="h-3 w-3" />
                {open}
              </span>
            )}
          </span>
        )}
      </button>
    </div>
  );
}

function WeekDetails({ info }: { info: DayInfo }) {
  const reminders = activeReminders(info);
  return (
    <span aria-hidden="true" className="relative flex min-w-0 flex-col gap-1 text-[11px] leading-snug sm:text-xs">
      {info.pins.map((pin) => (
        <span key={pin.id} className={`truncate rounded border px-1.5 py-0.5 ${pinMeta(pin.category).chip}`}>{pin.label}</span>
      ))}
      {reminders.map((reminder) => (
        <span key={reminder.id} className="flex min-w-0 items-center gap-1 text-warn-fg">
          <Bell className="h-3 w-3 shrink-0" />
          <span className="truncate">
            {new Date(reminder.remind_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })} {reminder.note}
          </span>
        </span>
      ))}
      {info.todos.slice(0, 5).map((todo) => (
        <span key={todo.id} className={`truncate ${todo.done ? "text-fg-subtle line-through" : "text-fg-soft"}`}>
          {todo.done ? "☑" : "☐"} {todo.text}
        </span>
      ))}
      {info.journalSnippet && <span className="line-clamp-3 font-serif italic text-fg-muted">“{info.journalSnippet}”</span>}
      {info.sharedNotes > 0 && <span className="flex items-center gap-1 text-info-fg"><Users className="h-3 w-3 shrink-0" />{info.sharedNotes === 1 ? "Shared note" : `${info.sharedNotes} shared notes`}</span>}
      {info.entries > 0 && <span className="text-link">{info.entries} project {info.entries === 1 ? "entry" : "entries"}</span>}
    </span>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-fg-muted" aria-label="Legend">
      <span className="flex items-center gap-1.5">
        Less
        {HEAT_CLASSES.map((tint, index) => (
          <span key={index} aria-hidden="true" className="h-3 w-3 overflow-hidden rounded-sm border border-line bg-surface">
            <span className={`block h-full w-full ${tint}`} />
          </span>
        ))}
        More writing
      </span>
      {PIN_CATEGORIES.map((category) => (
        <span key={category.id} className="flex items-center gap-1.5">
          <span aria-hidden="true" className={`h-2 w-2 rounded-full ${category.dot}`} />
          {category.label}
        </span>
      ))}
      <span className="flex items-center gap-1.5"><Bell className="h-3 w-3 text-warn-fg" aria-hidden="true" />Reminder</span>
      <span className="flex items-center gap-1.5"><NotebookPen className="h-3 w-3 text-link" aria-hidden="true" />Written</span>
      <span className="flex items-center gap-1.5"><Users className="h-3 w-3 text-info-fg" aria-hidden="true" />Shared with supervisor</span>
    </div>
  );
}

// On small screens the month grid stays compact; the selected week is
// listed below it as an agenda.
function Agenda({ days, info, onOpen, hidden }: { days: ISODate[]; info: Map<ISODate, DayInfo>; onOpen: (day: ISODate) => void; hidden: boolean }) {
  if (hidden) return null;
  return (
    <section aria-label="Agenda for the selected week" className="md:hidden">
      <h3 className="mb-2 text-sm font-semibold text-fg">This week</h3>
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
        {days.map((day) => {
          const item = info.get(day) ?? EMPTY_DAY;
          const open = openTodoCount(item);
          const reminders = activeReminders(item);
          const empty = !item.pins.length && !reminders.length && !open && !item.journalWords && !item.entries && !item.sharedNotes;
          return (
            <li key={day}>
              <button type="button" onClick={() => onOpen(day)} className="flex w-full gap-3 px-3 py-2.5 text-left hover:bg-surface-muted">
                <span className={`w-12 shrink-0 text-center ${day === todayDay() ? "text-link" : "text-fg-muted"}`}>
                  <span className="block text-[10px] font-semibold uppercase">{parseDay(day).toLocaleDateString(undefined, { weekday: "short" })}</span>
                  <span className="block font-serif text-lg font-semibold leading-tight text-fg">{Number(day.slice(8))}</span>
                </span>
                <span className="min-w-0 flex-1 space-y-1 text-sm">
                  {empty && <span className="text-fg-subtle">Nothing yet. Tap to plan or write.</span>}
                  {item.pins.map((pin) => (
                    <span key={pin.id} className="flex items-center gap-1.5 text-fg-soft">
                      <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${pinMeta(pin.category).dot}`} />
                      <span className="truncate">{pin.label}</span>
                    </span>
                  ))}
                  {reminders.map((reminder) => (
                    <span key={reminder.id} className="flex items-center gap-1.5 text-warn-fg">
                      <Bell className="h-3 w-3 shrink-0" aria-hidden="true" />
                      <span className="truncate">{new Date(reminder.remind_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })} · {reminder.note}</span>
                    </span>
                  ))}
                  {(open > 0 || item.journalWords > 0 || item.entries > 0 || item.sharedNotes > 0) && (
                    <span className="block text-xs text-fg-muted">
                      {[
                        item.journalWords > 0 && "Journal written",
                        item.entries > 0 && `${item.entries} project ${item.entries === 1 ? "entry" : "entries"}`,
                        item.sharedNotes > 0 && (item.sharedNotes === 1 ? "Shared note" : `${item.sharedNotes} shared notes`),
                        open > 0 && `${open} open to-do${open === 1 ? "" : "s"}`,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
