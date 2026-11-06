import api from "./api";
import { cleanParams, type MessageResponse, type Page, type QueryParams } from "./types";

export type ReadingStatus = "not_started" | "reading" | "completed";

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  publication_year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  keywords: string[];
  added_by: string | null;
  created_at: string;
  updated_at: string;
  projects: { id: string; title: string }[];
  my_status: ReadingStatus | null;
  can_edit: boolean;
  linked_existing: boolean;
  discord_thread_url: string | null;
}

export interface DoiLookup {
  title: string | null;
  authors: string[];
  abstract: string;
  publication_year: number | null;
  venue: string | null;
  doi: string;
  url: string | null;
  keywords: string[];
  existing_paper_id: string | null;
}

export interface PaperInput {
  title: string;
  authors: string[];
  abstract: string;
  publication_year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  keywords: string[];
  project_id?: string | null;
}

export interface Note {
  id: string;
  paper_id: string;
  project_id: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ReadingProgress {
  paper_id: string;
  paper_title: string | null;
  project_id: string | null;
  user_id: string;
  username: string | null;
  status: ReadingStatus;
  updated_at: string;
}

const base = "/api/v1/research";

export const listPapers = async (params: QueryParams = {}) =>
  (await api.get<Page<Paper>>(`${base}/papers`, { params: cleanParams(params) })).data;
export const lookupDoi = async (doi: string) =>
  (await api.get<DoiLookup>(`${base}/lookup`, { params: { doi } })).data;
export const getPaper = async (id: string) => (await api.get<Paper>(`${base}/papers/${id}`)).data;
export const createPaper = async (input: PaperInput) => (await api.post<Paper>(`${base}/papers`, input)).data;
export const updatePaper = async (id: string, input: Partial<PaperInput>) =>
  (await api.patch<Paper>(`${base}/papers/${id}`, input)).data;
export const linkPaper = async (id: string, projectId: string) =>
  (await api.post<Paper>(`${base}/papers/${id}/projects`, { project_id: projectId })).data;
export const unlinkPaper = async (id: string, projectId: string) =>
  (await api.delete<MessageResponse>(`${base}/papers/${id}/projects/${projectId}`)).data;
export const setReadingStatus = async (id: string, status: ReadingStatus, projectId?: string | null) =>
  (await api.put<ReadingProgress>(`${base}/papers/${id}/progress`, { status, project_id: projectId ?? null })).data;
export const projectReadingProgress = async (projectId: string) =>
  (await api.get<ReadingProgress[]>(`${base}/projects/${projectId}/progress`)).data;
export const listNotes = async (paperId: string) => (await api.get<Note[]>(`${base}/papers/${paperId}/notes`)).data;
export const createNote = async (paperId: string, content: string) =>
  (await api.post<Note>(`${base}/papers/${paperId}/notes`, { content })).data;
export const updateNote = async (noteId: string, content: string) =>
  (await api.patch<Note>(`${base}/notes/${noteId}`, { content })).data;
export const deleteNote = async (noteId: string) =>
  (await api.delete<MessageResponse>(`${base}/notes/${noteId}`)).data;
