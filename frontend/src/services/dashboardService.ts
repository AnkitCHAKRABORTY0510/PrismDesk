import api from "./api";
import { cleanParams, type Page, type QueryParams } from "./types";

export interface CountMap {
  counts: Record<string, number>;
  total: number;
}

export interface DeadlineItem {
  id: string;
  title: string;
  due_at: string;
  kind: "task" | "conference";
  project_id: string | null;
  project_title: string | null;
  status: string | null;
}

export interface ActivityItem {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_username: string | null;
  created_at: string;
}

export interface ProjectSummaryItem {
  id: string;
  title: string;
  status: string;
  my_role: string | null;
  member_count: number;
  assignments_total: number;
  assignments_completed: number;
  pending_reviews: number;
  overdue: number;
}

export interface HandbookItem {
  id: string;
  entry_date: string;
  student_username: string;
  project_id: string;
  project_title: string;
  comment_count: number;
}

export interface ReviewItem {
  assignment_id: string;
  task_id: string;
  task_title: string;
  student_username: string;
  project_title: string;
  submitted_at: string | null;
}

export interface AdminDashboardData {
  users: CountMap;
  projects: CountMap;
  research_papers: number;
  tasks: CountMap;
  overdue_assignments: number;
  notifications: CountMap;
  upcoming_conferences: DeadlineItem[];
  recent_activity: ActivityItem[];
}

export interface ProfessorDashboardData {
  supervised_projects: ProjectSummaryItem[];
  member_count: number;
  pending_reviews: number;
  review_queue: ReviewItem[];
  recent_handbook_entries: HandbookItem[];
  upcoming_deadlines: DeadlineItem[];
  reading_progress: CountMap;
}

export interface StudentDashboardData {
  joined_projects: ProjectSummaryItem[];
  owned_project_count: number;
  assigned_tasks: CountMap;
  personal_tasks: CountMap;
  pending_submissions: number;
  task_completion_rate: number;
  reading_progress: CountMap;
  handbook_entries_last_7_days: number;
  handbook_entries_last_30_days: number;
  recent_handbook_entries: HandbookItem[];
  upcoming_deadlines: DeadlineItem[];
}

export interface GuestDashboardData {
  projects: ProjectSummaryItem[];
  paper_count: number;
  upcoming_conferences: DeadlineItem[];
}

export interface ProjectAnalyticsData {
  project_id: string;
  assignments: CountMap;
  completion_rate: number;
  overdue_assignments: number;
  reading_progress: CountMap;
  paper_count: number;
  handbook_per_week: { week_start: string; count: number }[];
  activity_last_30_days: number;
  upcoming_deadlines: DeadlineItem[];
}

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  actor_username: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

const base = "/api/v1/dashboard";

export const adminDashboard = async () => (await api.get<AdminDashboardData>(`${base}/admin`)).data;
export const professorDashboard = async () => (await api.get<ProfessorDashboardData>(`${base}/professor`)).data;
export const studentDashboard = async () => (await api.get<StudentDashboardData>(`${base}/student`)).data;
export const guestDashboard = async () => (await api.get<GuestDashboardData>(`${base}/guest`)).data;
export const projectAnalytics = async (projectId: string) =>
  (await api.get<ProjectAnalyticsData>(`${base}/projects/${projectId}`)).data;
export const systemSettings = async () => (await api.get<Record<string, unknown>>(`${base}/system-settings`)).data;
export const auditLogs = async (params: QueryParams = {}) =>
  (await api.get<Page<AuditLogEntry>>("/api/v1/audit/logs", { params: cleanParams(params) })).data;
