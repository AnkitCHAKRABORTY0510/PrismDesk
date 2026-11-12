import { useState, type FormEvent, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Bell, BellOff, BellRing, CalendarArrowUp, GripVertical, Pin as PinIcon, Plus, Trash2 } from "lucide-react";

import { Button, Input, useToast } from "../../components/ui";
import { useNow } from "../../hooks/useNow";
import { addDays, longDayLabel, type ISODate } from "../../lib/calendar";
import { getErrorMessage } from "../../services/api";
import {
  carryForward,
  createPin,
  createReminder,
  createTodo,
  deletePin,
  deleteReminder,
  deleteTodo,
  reorderTodos,
  updateReminder,
  updateTodo,
  type Pin,
  type PinCategory,
  type Reminder,
  type Todo,
} from "../../services/handbookPlannerService";
import { PIN_CATEGORIES, pinMeta } from "./plannerMeta";

// Run an API action and report failures as a toast; returns success.
function useAction(onChanged: () => void) {
  const { notify } = useToast();
  const [busy, setBusy] = useState(false);
  const run = async (action: () => Promise<unknown>, success?: string) => {
    setBusy(true);
    try {
      await action();
      if (success) notify(success);
      onChanged();
      return true;
    } catch (err) {
      notify(getErrorMessage(err), "error");
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

function PanelEmpty({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line-strong px-4 py-6 text-center text-sm text-fg-muted">{children}</p>;
}

// --- To-dos ----------------------------------------------------------------------

export function TodoPanel({ day, todos, onChanged }: { day: ISODate; todos: Todo[]; onChanged: () => void }) {
  const [text, setText] = useState("");
  const [dragId, setDragId] = useState<string | null>(null);
  const { busy, run } = useAction(onChanged);
  const ordered = [...todos].sort((a, b) => a.position - b.position);
  const open = ordered.filter((todo) => !todo.done).length;
  const tomorrow = addDays(day, 1);

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    if (await run(() => createTodo(day, text.trim()))) setText("");
  };

  const move = (ids: string[]) => run(() => reorderTodos(day, ids));
  const swap = (index: number, delta: number) => {
    const ids = ordered.map((todo) => todo.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    void move(ids);
  };
  const dropOn = (targetId: string) => {
    if (!dragId || dragId === targetId) return;
    const ids = ordered.map((todo) => todo.id).filter((id) => id !== dragId);
    ids.splice(ids.indexOf(targetId), 0, dragId);
    setDragId(null);
    void move(ids);
  };

  return (
    <section aria-label="To-dos" className="space-y-4">
      <form onSubmit={add} className="flex gap-2">
        <Input aria-label="New to-do" placeholder="Add a to-do…" value={text} maxLength={500} onChange={(e) => setText(e.target.value)} />
        <Button type="submit" disabled={!text.trim() || busy}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add
        </Button>
      </form>
      {ordered.length === 0 ? (
        <PanelEmpty>No to-dos for this day yet. Plan ahead: future days work too.</PanelEmpty>
      ) : (
        <ul className="divide-y divide-line rounded-lg border border-line">
          {ordered.map((todo, index) => (
            <li
              key={todo.id}
              draggable
              onDragStart={() => setDragId(todo.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => dropOn(todo.id)}
              className={`group flex items-center gap-2 px-2 py-2 ${dragId === todo.id ? "opacity-50" : ""}`}
            >
              <GripVertical className="h-4 w-4 shrink-0 cursor-grab text-fg-subtle" aria-hidden="true" />
              <input
                type="checkbox"
                checked={todo.done}
                aria-label={`Mark "${todo.text}" as ${todo.done ? "not done" : "done"}`}
                onChange={() => void run(() => updateTodo(todo.id, { done: !todo.done }))}
                className="h-4 w-4 shrink-0 accent-[var(--primary)]"
              />
              <span className={`min-w-0 flex-1 break-words text-sm ${todo.done ? "text-fg-subtle line-through" : "text-fg"}`}>{todo.text}</span>
              <span className="flex shrink-0 items-center opacity-100 sm:opacity-0 sm:transition-opacity sm:group-focus-within:opacity-100 sm:group-hover:opacity-100">
                <SmallIcon label={`Move "${todo.text}" up`} disabled={index === 0 || busy} onClick={() => swap(index, -1)}>
                  <ArrowUp className="h-3.5 w-3.5" />
                </SmallIcon>
                <SmallIcon label={`Move "${todo.text}" down`} disabled={index === ordered.length - 1 || busy} onClick={() => swap(index, 1)}>
                  <ArrowDown className="h-3.5 w-3.5" />
                </SmallIcon>
                <SmallIcon label={`Delete "${todo.text}"`} danger onClick={() => void run(() => deleteTodo(todo.id))}>
                  <Trash2 className="h-3.5 w-3.5" />
                </SmallIcon>
              </span>
            </li>
          ))}
        </ul>
      )}
      {open > 0 && (
        <Button
          variant="secondary"
          size="sm"
          disabled={busy}
          onClick={() => void run(() => carryForward(day, tomorrow), `Moved ${open} unfinished to-do${open === 1 ? "" : "s"} to ${longDayLabel(tomorrow)}.`)}
        >
          <CalendarArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
          Carry {open} unfinished to tomorrow
        </Button>
      )}
    </section>
  );
}

function SmallIcon({
  label,
  onClick,
  disabled = false,
  danger = false,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex h-7 w-7 items-center justify-center rounded-md text-fg-muted transition-colors disabled:opacity-30 ${
        danger ? "hover:bg-danger-soft hover:text-danger-fg" : "hover:bg-surface-muted hover:text-fg"
      }`}
    >
      {children}
    </button>
  );
}

// --- Reminders -------------------------------------------------------------------

function notificationState(): NotificationPermission | "unsupported" {
  return typeof window !== "undefined" && "Notification" in window ? Notification.permission : "unsupported";
}

export function ReminderPanel({ day, reminders, onChanged }: { day: ISODate; reminders: Reminder[]; onChanged: () => void }) {
  const [time, setTime] = useState("09:00");
  const [note, setNote] = useState("");
  const [permission, setPermission] = useState(notificationState);
  const { busy, run } = useAction(onChanged);
  const now = useNow(30_000).getTime();
  const sorted = [...reminders].sort((a, b) => a.remind_at.localeCompare(b.remind_at));

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!note.trim() || !time) return;
    const remindAt = new Date(`${day}T${time}`).toISOString();
    if (await run(() => createReminder({ reminder_date: day, remind_at: remindAt, note: note.trim() }), "Reminder set.")) setNote("");
  };

  const askPermission = async () => {
    if (permission === "unsupported") return;
    setPermission(await Notification.requestPermission());
  };

  return (
    <section aria-label="Reminders" className="space-y-4">
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-[8rem_1fr_auto]">
        <Input aria-label="Reminder time" type="time" required value={time} onChange={(e) => setTime(e.target.value)} />
        <Input aria-label="Reminder note" placeholder="Remind me to…" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
        <Button type="submit" disabled={!note.trim() || busy}>
          <Bell className="h-4 w-4" aria-hidden="true" />
          Remind me
        </Button>
      </form>
      {permission === "default" && (
        <p className="flex flex-wrap items-center gap-2 text-xs text-fg-muted">
          Reminders show inside Prism Desk. Want them as desktop notifications too?
          <button type="button" onClick={() => void askPermission()} className="font-medium text-link underline underline-offset-2">
            Allow browser notifications
          </button>
        </p>
      )}
      {permission === "denied" && <p className="text-xs text-fg-muted">Browser notifications are blocked for this site, so reminders appear inside Prism Desk only.</p>}
      {sorted.length === 0 ? (
        <PanelEmpty>No reminders on this day.</PanelEmpty>
      ) : (
        <ul className="space-y-2">
          {sorted.map((reminder) => {
            const due = new Date(reminder.remind_at).getTime() <= now;
            const dismissed = Boolean(reminder.dismissed_at);
            return (
              <li
                key={reminder.id}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-sm ${
                  dismissed ? "border-line text-fg-subtle" : due ? "border-warn-line bg-warn-soft" : "border-line"
                }`}
              >
                {dismissed ? <BellOff className="h-4 w-4 shrink-0" aria-hidden="true" /> : due ? <BellRing className="h-4 w-4 shrink-0 text-warn-fg" aria-hidden="true" /> : <Bell className="h-4 w-4 shrink-0 text-fg-muted" aria-hidden="true" />}
                <span className="w-14 shrink-0 font-medium tabular-nums text-fg">
                  {new Date(reminder.remind_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className={`min-w-0 flex-1 break-words ${dismissed ? "line-through" : "text-fg-soft"}`}>{reminder.note}</span>
                <span className="sr-only">{dismissed ? "Done" : due ? "Due" : "Upcoming"}</span>
                {!dismissed && (
                  <Button size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => updateReminder(reminder.id, { dismissed: true }))}>
                    Done
                  </Button>
                )}
                <SmallIcon label={`Delete reminder "${reminder.note}"`} danger onClick={() => void run(() => deleteReminder(reminder.id))}>
                  <Trash2 className="h-3.5 w-3.5" />
                </SmallIcon>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// --- Pins ------------------------------------------------------------------------

export function PinPanel({ day, pins, onChanged }: { day: ISODate; pins: Pin[]; onChanged: () => void }) {
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState<PinCategory>("deadline");
  const [note, setNote] = useState("");
  const { busy, run } = useAction(onChanged);

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!label.trim()) return;
    if (await run(() => createPin({ pin_date: day, label: label.trim(), category, note: note.trim() }), "Pinned to the calendar.")) {
      setLabel("");
      setNote("");
    }
  };

  return (
    <section aria-label="Pins" className="space-y-4">
      <form onSubmit={add} className="space-y-3">
        <fieldset>
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">Category</legend>
          <div className="flex flex-wrap gap-2">
            {PIN_CATEGORIES.map((option) => (
              <label
                key={option.id}
                className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-shadow has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring ${
                  category === option.id ? `${option.chip} shadow-sm` : "border-line text-fg-muted hover:border-line-strong"
                }`}
              >
                <input type="radio" name="pin-category" value={option.id} checked={category === option.id} onChange={() => setCategory(option.id)} className="sr-only" />
                <span aria-hidden="true" className={`h-2 w-2 rounded-full ${option.dot}`} />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <Input aria-label="Pin label" placeholder="e.g. Paper deadline" maxLength={120} value={label} onChange={(e) => setLabel(e.target.value)} />
          <Input aria-label="Pin note (optional)" placeholder="Note (optional)" maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
          <Button type="submit" disabled={!label.trim() || busy}>
            <PinIcon className="h-4 w-4" aria-hidden="true" />
            Pin
          </Button>
        </div>
      </form>
      {pins.length === 0 ? (
        <PanelEmpty>No pins yet. Pin deadlines, meetings or ideas so they show on the calendar.</PanelEmpty>
      ) : (
        <ul className="space-y-2">
          {pins.map((pin) => {
            const meta = pinMeta(pin.category);
            return (
              <li key={pin.id} className={`flex items-start gap-3 rounded-lg border px-3 py-2 text-sm ${meta.chip}`}>
                <span aria-hidden="true" className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${meta.dot}`} />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{pin.label}</span>
                  <span className="block text-xs opacity-80">{meta.label}{pin.note ? ` · ${pin.note}` : ""}</span>
                </span>
                <SmallIcon label={`Remove pin "${pin.label}"`} danger onClick={() => void run(() => deletePin(pin.id))}>
                  <Trash2 className="h-3.5 w-3.5" />
                </SmallIcon>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
