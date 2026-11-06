import api from "./api";
import { cleanParams, type MessageResponse, type Page, type QueryParams } from "./types";

export interface ImportantDate {
  label: string;
  date: string;
}

export interface Conference {
  id: string;
  name: string;
  acronym: string | null;
  website_url: string | null;
  cfp_url: string | null;
  submission_deadline: string;
  important_dates: ImportantDate[];
  location: string | null;
  notes: string;
  added_by: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  seconds_remaining: number;
  projects: { project_id: string; project_title: string; status: "active" | "archived"; added_at: string; can_manage: boolean }[];
  can_edit: boolean;
  linked_existing: boolean;
}

export interface ConferenceInput {
  name: string;
  acronym: string | null;
  website_url: string | null;
  cfp_url: string | null;
  submission_deadline: string;
  important_dates: ImportantDate[];
  location: string | null;
  notes: string;
  project_id?: string | null;
}

const base = "/api/v1/conferences";

export const listConferences = async (params: QueryParams = {}) =>
  (await api.get<Page<Conference>>(base, { params: cleanParams(params) })).data;
export const getConference = async (id: string) => (await api.get<Conference>(`${base}/${id}`)).data;
export const createConference = async (input: ConferenceInput) => (await api.post<Conference>(base, input)).data;
export const updateConference = async (id: string, input: Partial<ConferenceInput>) =>
  (await api.patch<Conference>(`${base}/${id}`, input)).data;
export const deleteConference = async (id: string) => (await api.delete<MessageResponse>(`${base}/${id}`)).data;
export const linkConference = async (id: string, projectId: string) =>
  (await api.post<Conference>(`${base}/${id}/projects`, { project_id: projectId })).data;
export const archiveConferenceLink = async (id: string, projectId: string) =>
  (await api.post<MessageResponse>(`${base}/${id}/projects/${projectId}/archive`)).data;
export const unlinkConference = async (id: string, projectId: string) =>
  (await api.delete<MessageResponse>(`${base}/${id}/projects/${projectId}`)).data;
