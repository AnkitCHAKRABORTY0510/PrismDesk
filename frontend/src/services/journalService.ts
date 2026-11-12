import api from "./api";
import { cleanParams, type MessageResponse, type Page, type QueryParams } from "./types";

export type Quartile = "Q1" | "Q2" | "Q3" | "Q4";

export interface Journal {
  id: string;
  title: string;
  issn: string | null;
  publisher: string | null;
  homepage_url: string | null;
  sjr_quartile: Quartile | null;
  sjr: number | null;
  h_index: number | null;
  subject_areas: string[];
  is_open_access: boolean;
  notes: string;
  special_issue_title: string | null;
  submission_deadline: string | null;
  project_id: string | null;
  project_title: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  seconds_remaining: number | null;
  wikicfp_url: string;
  google_special_issues_url: string;
  linked_existing: boolean;
}

export interface JournalInput {
  title: string;
  issn: string | null;
  publisher: string | null;
  homepage_url: string | null;
  sjr_quartile: Quartile | null;
  is_open_access: boolean;
  notes: string;
  special_issue_title: string | null;
  submission_deadline: string | null;
  project_id?: string | null;
}

export interface CatalogJournal {
  issn: string | null;
  issns: string[];
  title: string;
  publisher: string | null;
  homepage_url: string | null;
  areas: string[];
  domains: string[];
  categories: { name: string; quartile: string | null }[];
  sjr: number | null;
  sjr_quartile: Quartile | null;
  sjr_rank: number | null;
  h_index: number | null;
  country: string | null;
  two_year_mean_citedness: number | null;
  works_count: number | null;
  cited_by_count: number | null;
  is_oa: boolean;
  is_in_doaj: boolean;
  apc_usd: number | null;
  openalex_id: string | null;
  openalex_url: string | null;
  sjr_url: string | null;
  enriched: boolean;
  submission_mode: "rolling";
  wikicfp_url: string;
  google_special_issues_url: string;
  in_my_list: boolean;
  my_journal_id: string | null;
}

export interface CatalogSourceInfo {
  name: string;
  url: string;
  license: string;
  available: boolean;
  fetched_at: string | null;
  stale: boolean;
  note: string | null;
}

export interface JournalCatalogPage {
  items: CatalogJournal[];
  total: number;
  total_is_estimate: boolean;
  limit: number;
  offset: number;
  mode: "sjr" | "openalex";
  ranking_available: boolean;
  ranking: CatalogSourceInfo;
  metadata: CatalogSourceInfo;
  domains: { id: string; label: string }[];
}

const base = "/api/v1/journals";

export const listJournals = async (params: QueryParams = {}) =>
  (await api.get<Page<Journal>>(base, { params: cleanParams(params) })).data;
export const createJournal = async (input: JournalInput) => (await api.post<Journal>(base, input)).data;
export const updateJournal = async (id: string, input: Partial<JournalInput>) =>
  (await api.patch<Journal>(`${base}/${id}`, input)).data;
export const deleteJournal = async (id: string) => (await api.delete<MessageResponse>(`${base}/${id}`)).data;

export const browseJournalCatalog = async (params: QueryParams = {}) =>
  (await api.get<JournalCatalogPage>(`${base}/catalog`, { params: cleanParams(params) })).data;
export const refreshJournalCatalog = async () =>
  (
    await api.post<{ ranking_available: boolean; total: number; fetched_at: string | null; stale: boolean; note: string | null }>(
      `${base}/catalog/refresh`
    )
  ).data;
export const addCatalogJournal = async (issn: string, projectId?: string | null) =>
  (await api.post<Journal>(`${base}/catalog/${encodeURIComponent(issn)}/add`, projectId ? { project_id: projectId } : {})).data;
