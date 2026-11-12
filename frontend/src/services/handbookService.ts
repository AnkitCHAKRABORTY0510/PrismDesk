import api from "./api";
import { cleanParams, type Page, type QueryParams, type UserSummary } from "./types";

export interface HandbookComment {
  id: string;
  entry_id: string;
  parent_id: string | null;
  author: UserSummary | null;
  body: string;
  created_at: string;
  replies: HandbookComment[];
}

export interface HandbookEntry {
  id: string;
  student: UserSummary;
  project_id: string;
  project_title: string | null;
  entry_date: string;
  work_completed: string;
  research_progress: string;
  problems: string;
  next_steps: string;
  references: string[];
  version: number;
  created_at: string;
  updated_at: string;
  comment_count: number;
  comments: HandbookComment[];
  can_edit: boolean;
  can_comment: boolean;
}

export interface EntryInput {
  project_id: string;
  entry_date: string;
  work_completed: string;
  research_progress: string;
  problems: string;
  next_steps: string;
  references: string[];
}

export interface Version {
  version: number;
  snapshot: Record<string, unknown>;
  edited_at: string;
}

export interface DailySummary {
  id: string;
  entry_date: string;
  summary: string;
  challenges: string;
  plan_next: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProgressDay {
  entry_date: string;
  entry_count: number;
  student_count: number;
}

const base = "/api/v1/handbook";

export const listEntries = async (params: QueryParams = {}) =>
  (await api.get<Page<HandbookEntry>>(`${base}/entries`, { params: cleanParams(params) })).data;
export const getEntry = async (id: string) => (await api.get<HandbookEntry>(`${base}/entries/${id}`)).data;
export const createEntry = async (input: EntryInput) =>
  (await api.post<HandbookEntry>(`${base}/entries`, input)).data;
export const updateEntry = async (id: string, input: Partial<Omit<EntryInput, "project_id" | "entry_date">>) =>
  (await api.patch<HandbookEntry>(`${base}/entries/${id}`, input)).data;
export const entryVersions = async (id: string) => (await api.get<Version[]>(`${base}/entries/${id}/versions`)).data;
export const addComment = async (id: string, body: string, parentId?: string) =>
  (await api.post<HandbookEntry>(`${base}/entries/${id}/comments`, { body, parent_id: parentId ?? null })).data;
export const progress = async (params: QueryParams = {}) =>
  (await api.get<ProgressDay[]>(`${base}/progress`, { params: cleanParams(params) })).data;
export const listSummaries = async (params: QueryParams = {}) =>
  (await api.get<Page<DailySummary>>(`${base}/summaries`, { params: cleanParams(params) })).data;
export const createSummary = async (input: Omit<DailySummary, "id" | "version" | "created_at" | "updated_at">) =>
  (await api.post<DailySummary>(`${base}/summaries`, input)).data;
export const updateSummary = async (id: string, input: Partial<Pick<DailySummary, "summary" | "challenges" | "plan_next">>) =>
  (await api.patch<DailySummary>(`${base}/summaries/${id}`, input)).data;
export const summaryVersions = async (id: string) =>
  (await api.get<Version[]>(`${base}/summaries/${id}/versions`)).data;

// --- Shared notes: written by a student for their supervisors -------------

export interface SharedComment {
  id: string;
  note_id: string;
  parent_id: string | null;
  author: UserSummary | null;
  body: string;
  created_at: string;
  replies: SharedComment[];
}

export interface SharedNote {
  id: string;
  student: UserSummary;
  entry_date: string;
  body: string;
  version: number;
  created_at: string;
  updated_at: string;
  comment_count: number;
  comments: SharedComment[];
  can_edit: boolean;
  can_comment: boolean;
}

export const listSharedNotes = async (params: QueryParams = {}) =>
  (await api.get<Page<SharedNote>>(`${base}/shared-notes`, { params: cleanParams(params) })).data;
export const getSharedNote = async (id: string) => (await api.get<SharedNote>(`${base}/shared-notes/${id}`)).data;
export const createSharedNote = async (entryDate: string, body: string) =>
  (await api.post<SharedNote>(`${base}/shared-notes`, { entry_date: entryDate, body })).data;
export const updateSharedNote = async (id: string, body: string) =>
  (await api.patch<SharedNote>(`${base}/shared-notes/${id}`, { body })).data;
export const sharedNoteVersions = async (id: string) =>
  (await api.get<Version[]>(`${base}/shared-notes/${id}/versions`)).data;
export const addSharedComment = async (id: string, body: string, parentId?: string) =>
  (await api.post<SharedNote>(`${base}/shared-notes/${id}/comments`, { body, parent_id: parentId ?? null })).data;
