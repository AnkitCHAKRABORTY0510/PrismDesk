import api from "./api";
import { cleanParams, type MessageResponse, type Page, type QueryParams, type UserSummary } from "./types";

/** "reminder": a nudge sent to other users, usually about a related official task. */
export type TaskType = "official" | "personal" | "reminder";
export type TaskPriority = "low" | "medium" | "high" | "urgent";
export type AssignmentStatus = "todo" | "in_progress" | "under_review" | "revision_required" | "completed";

export interface Assignment {
  id: string;
  task_id: string;
  assignee: UserSummary;
  status: AssignmentStatus;
  assigned_at: string;
  submitted_at: string | null;
  completed_at: string | null;
  updated_at: string;
  submission_count: number;
}

export interface Task {
  id: string;
  task_type: TaskType;
  title: string;
  description: string;
  project_id: string | null;
  project_title: string | null;
  created_by: string | null;
  priority: TaskPriority;
  due_at: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  my_assignment: Assignment | null;
  assignments: Assignment[];
  can_manage: boolean;
  // Always sent by the server; optional so older fixtures stay valid.
  created_by_user?: UserSummary | null;
  related_task_id?: string | null;
  related_task_title?: string | null;
}

export interface ReminderRecipient {
  user: UserSummary;
  membership_role: string;
}

export interface Review {
  id: string;
  reviewer: UserSummary | null;
  decision: "approved" | "revision_required";
  feedback: string;
  created_at: string;
}

export interface Submission {
  id: string;
  assignment_id: string;
  version: number;
  response_text: string;
  links: string[];
  submitted_at: string;
  reviews: Review[];
}

export interface PendingReview {
  assignment: Assignment;
  task_id: string;
  task_title: string;
  project_id: string | null;
  project_title: string | null;
  latest_submission_id: string | null;
  latest_version: number | null;
  submitted_at: string | null;
}

export interface TaskInput {
  task_type: TaskType;
  title: string;
  description: string;
  project_id: string | null;
  priority: TaskPriority;
  due_at: string | null;
  assignee_ids: string[];
  related_task_id?: string | null;
}

const base = "/api/v1/tasks";

export const listTasks = async (params: QueryParams = {}) =>
  (await api.get<Page<Task>>(base, { params: cleanParams(params) })).data;
export const getTask = async (id: string) => (await api.get<Task>(`${base}/${id}`)).data;
export const createTask = async (input: TaskInput) => (await api.post<Task>(base, input)).data;
export const updateTask = async (
  id: string,
  input: Partial<Pick<TaskInput, "title" | "description" | "priority" | "due_at">> & { clear_due_at?: boolean }
) => (await api.patch<Task>(`${base}/${id}`, input)).data;
export const deleteTask = async (id: string) => (await api.delete<MessageResponse>(`${base}/${id}`)).data;
export const addAssignees = async (id: string, assigneeIds: string[]) =>
  (await api.post<Task>(`${base}/${id}/assignees`, { assignee_ids: assigneeIds })).data;
export const removeAssignee = async (id: string, assigneeId: string) =>
  (await api.delete<MessageResponse>(`${base}/${id}/assignees/${assigneeId}`)).data;
export const changeStatus = async (assignmentId: string, status: AssignmentStatus) =>
  (await api.patch<Assignment>(`${base}/assignments/${assignmentId}/status`, { status })).data;
export const listSubmissions = async (assignmentId: string) =>
  (await api.get<Submission[]>(`${base}/assignments/${assignmentId}/submissions`)).data;
export const submitWork = async (assignmentId: string, responseText: string, links: string[]) =>
  (await api.post<Submission>(`${base}/assignments/${assignmentId}/submissions`, { response_text: responseText, links })).data;
export const reviewSubmission = async (
  submissionId: string,
  decision: "approved" | "revision_required",
  feedback: string
) => (await api.post<Submission>(`${base}/submissions/${submissionId}/review`, { decision, feedback })).data;
export const pendingReviews = async (params: QueryParams = {}) =>
  (await api.get<Page<PendingReview>>(`${base}/reviews/pending`, { params: cleanParams(params) })).data;
/** Who the current user may remind, for a project or about one task. */
export const reminderRecipients = async (params: { project_id?: string | null; related_task_id?: string | null }) =>
  (await api.get<ReminderRecipient[]>(`${base}/reminder-recipients`, { params: cleanParams(params) })).data;
