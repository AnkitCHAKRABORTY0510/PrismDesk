import api from "./api";

// Personal planner items on handbook calendar days. Private to their owner.

export type PinCategory = "deadline" | "meeting" | "milestone" | "idea" | "other";

export interface Pin {
  id: string;
  pin_date: string;
  label: string;
  category: PinCategory;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface Todo {
  id: string;
  todo_date: string;
  text: string;
  done: boolean;
  position: number;
  done_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Reminder {
  id: string;
  reminder_date: string;
  remind_at: string;
  note: string;
  dismissed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlannerRange {
  pins: Pin[];
  todos: Todo[];
  reminders: Reminder[];
}

const base = "/api/v1/handbook";

// Other parts of the app (the reminder watcher, the side rail) listen for
// this to refresh after any planner change.
export const PLANNER_CHANGED = "handbook:planner-changed";
function changed<T>(value: T): T {
  window.dispatchEvent(new Event(PLANNER_CHANGED));
  return value;
}

export const getPlanner = async (dateFrom: string, dateTo: string) =>
  (await api.get<PlannerRange>(`${base}/planner`, { params: { date_from: dateFrom, date_to: dateTo } })).data;

export const createPin = async (input: Pick<Pin, "pin_date" | "label" | "category" | "note">) =>
  changed((await api.post<Pin>(`${base}/pins`, input)).data);
export const updatePin = async (id: string, input: Partial<Pick<Pin, "pin_date" | "label" | "category" | "note">>) =>
  changed((await api.patch<Pin>(`${base}/pins/${id}`, input)).data);
export const deletePin = async (id: string) => changed(void (await api.delete(`${base}/pins/${id}`)));

export const openTodos = async (limit = 20) =>
  (await api.get<Todo[]>(`${base}/todos/open`, { params: { limit } })).data;
export const createTodo = async (todoDate: string, text: string) =>
  changed((await api.post<Todo>(`${base}/todos`, { todo_date: todoDate, text })).data);
export const updateTodo = async (id: string, input: Partial<Pick<Todo, "todo_date" | "text" | "done">>) =>
  changed((await api.patch<Todo>(`${base}/todos/${id}`, input)).data);
export const deleteTodo = async (id: string) => changed(void (await api.delete(`${base}/todos/${id}`)));
export const reorderTodos = async (todoDate: string, ids: string[]) =>
  changed((await api.post<Todo[]>(`${base}/todos/reorder`, { todo_date: todoDate, ids })).data);
export const carryForward = async (fromDate: string, toDate: string) =>
  changed((await api.post<Todo[]>(`${base}/todos/carry-forward`, { from_date: fromDate, to_date: toDate })).data);

export const upcomingReminders = async (limit = 20) =>
  (await api.get<Reminder[]>(`${base}/reminders/upcoming`, { params: { limit } })).data;
export const createReminder = async (input: Pick<Reminder, "reminder_date" | "remind_at" | "note">) =>
  changed((await api.post<Reminder>(`${base}/reminders`, input)).data);
export const updateReminder = async (
  id: string,
  input: Partial<Pick<Reminder, "reminder_date" | "remind_at" | "note">> & { dismissed?: boolean }
) => changed((await api.patch<Reminder>(`${base}/reminders/${id}`, input)).data);
export const deleteReminder = async (id: string) => changed(void (await api.delete(`${base}/reminders/${id}`)));
