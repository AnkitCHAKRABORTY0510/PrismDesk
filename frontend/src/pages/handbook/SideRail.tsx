import { useEffect, type ReactNode } from "react";
import { Bell, BellRing, Flame, ListTodo, NotebookPen, Pin as PinIcon } from "lucide-react";

import { useAsync } from "../../hooks/useAsync";
import { useNow } from "../../hooks/useNow";
import { addDays, parseDay, today as todayDay, writingStreak, type ISODate } from "../../lib/calendar";
import { listSummaries, progress } from "../../services/handbookService";
import { PLANNER_CHANGED, openTodos, updateReminder, upcomingReminders, type Pin } from "../../services/handbookPlannerService";
import { pinMeta } from "./plannerMeta";

const STREAK_WINDOW = 99;

function shortDay(day: ISODate) {
  return parseDay(day).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

function RailCard({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-4 shadow-card">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-fg">
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

// Upcoming reminders, this month's pins, open to-dos, and writing stats.
export function SideRail({
  canWrite,
  period,
  monthPins,
  monthJournalDays,
  monthEntries,
  refreshKey,
  onOpen,
}: {
  canWrite: boolean;
  period: "month" | "week";
  monthPins: Pin[];
  monthJournalDays: number;
  monthEntries: number;
  refreshKey: number;
  onOpen: (day: ISODate) => void;
}) {
  const today = todayDay();
  const reminders = useAsync(() => upcomingReminders(6), [refreshKey]);
  const todos = useAsync(() => openTodos(8), [refreshKey]);
  const streak = useAsync(async () => {
    if (!canWrite) return 0;
    const from = addDays(today, -STREAK_WINDOW);
    const [days, journals] = await Promise.all([
      progress({ date_from: from, date_to: today }),
      listSummaries({ date_from: from, date_to: today, page_size: 100 }),
    ]);
    const active = new Set<ISODate>([...days.map((d) => d.entry_date), ...journals.items.map((s) => s.entry_date)]);
    return writingStreak(active, today);
  }, [refreshKey, canWrite]);

  const { reload: reloadReminders } = reminders;
  const { reload: reloadTodos } = todos;
  useEffect(() => {
    const handler = () => {
      void reloadReminders();
      void reloadTodos();
    };
    window.addEventListener(PLANNER_CHANGED, handler);
    return () => window.removeEventListener(PLANNER_CHANGED, handler);
  }, [reloadReminders, reloadTodos]);

  const now = useNow(30_000).getTime();

  return (
    <aside aria-label="Handbook overview" className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {canWrite && (
          <div className="rounded-xl border border-line bg-surface p-4 shadow-card">
            <Flame className="h-5 w-5 text-warn" aria-hidden="true" />
            <div className="mt-1 text-2xl font-semibold tabular-nums text-fg">{streak.data ?? "–"}</div>
            <div className="text-xs text-fg-muted">day writing streak</div>
          </div>
        )}
        <div className={`rounded-xl border border-line bg-surface p-4 shadow-card ${canWrite ? "" : "col-span-2"}`}>
          <NotebookPen className="h-5 w-5 text-link" aria-hidden="true" />
          <div className="mt-1 text-2xl font-semibold tabular-nums text-fg">{canWrite ? monthJournalDays : monthEntries}</div>
          <div className="text-xs text-fg-muted">{canWrite ? `journal days · ${monthEntries} project entries this ${period}` : `student entries this ${period}`}</div>
        </div>
      </div>

      <RailCard title="Upcoming reminders" icon={<Bell className="h-4 w-4 text-warn-fg" aria-hidden="true" />}>
        {(reminders.data ?? []).length === 0 ? (
          <p className="text-sm text-fg-muted">Nothing scheduled. Open a day to set one.</p>
        ) : (
          <ul className="space-y-2">
            {(reminders.data ?? []).map((reminder) => {
              const due = new Date(reminder.remind_at).getTime() <= now;
              return (
                <li key={reminder.id} className={`flex items-start gap-2 rounded-lg px-2 py-1.5 text-sm ${due ? "bg-warn-soft" : ""}`}>
                  {due ? <BellRing className="mt-0.5 h-4 w-4 shrink-0 text-warn-fg" aria-hidden="true" /> : <Bell className="mt-0.5 h-4 w-4 shrink-0 text-fg-subtle" aria-hidden="true" />}
                  <button type="button" onClick={() => onOpen(reminder.reminder_date)} className="min-w-0 flex-1 text-left">
                    <span className="block truncate text-fg-soft">{reminder.note}</span>
                    <span className="block text-xs text-fg-muted">
                      {due ? "Due · " : ""}
                      {shortDay(reminder.reminder_date)} · {new Date(reminder.remind_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </button>
                  {due && (
                    <button
                      type="button"
                      onClick={() => void updateReminder(reminder.id, { dismissed: true })}
                      className="shrink-0 rounded-md px-2 py-0.5 text-xs font-medium text-link hover:bg-surface-muted"
                      aria-label={`Mark reminder "${reminder.note}" done`}
                    >
                      Done
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </RailCard>

      <RailCard title={`Pinned this ${period}`} icon={<PinIcon className="h-4 w-4 text-danger-fg" aria-hidden="true" />}>
        {monthPins.length === 0 ? (
          <p className="text-sm text-fg-muted">No pins this {period}.</p>
        ) : (
          <ul className="space-y-1">
            {monthPins.map((pin) => (
              <li key={pin.id}>
                <button type="button" onClick={() => onOpen(pin.pin_date)} className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-surface-muted ${pin.pin_date < today ? "opacity-70" : ""}`}>
                  <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${pinMeta(pin.category).dot}`} />
                  <span className="min-w-0 flex-1 truncate text-fg-soft">{pin.label}</span>
                  <span className="shrink-0 text-xs text-fg-muted">{shortDay(pin.pin_date)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </RailCard>

      <RailCard title="Open to-dos" icon={<ListTodo className="h-4 w-4 text-success-fg" aria-hidden="true" />}>
        {(todos.data ?? []).length === 0 ? (
          <p className="text-sm text-fg-muted">All clear.</p>
        ) : (
          <ul className="space-y-1">
            {(todos.data ?? []).map((todo) => (
              <li key={todo.id}>
                <button type="button" onClick={() => onOpen(todo.todo_date)} className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-surface-muted">
                  <span aria-hidden="true" className="h-3.5 w-3.5 shrink-0 rounded border border-line-strong" />
                  <span className="min-w-0 flex-1 truncate text-fg-soft">{todo.text}</span>
                  <span className={`shrink-0 text-xs ${todo.todo_date < today ? "text-danger-fg" : "text-fg-muted"}`}>
                    {todo.todo_date < today ? "Overdue" : shortDay(todo.todo_date)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </RailCard>
    </aside>
  );
}
