import api from "./api";
import { cleanParams, type MessageResponse, type Page, type QueryParams, type UserSummary } from "./types";

export type ProjectStatus = "active" | "archived" | "deleted";
export type MembershipRole = "owner" | "supervisor" | "member" | "guest";

export interface ProjectPermissions {
  can_edit: boolean;
  can_contribute: boolean;
  can_manage_members: boolean;
  can_archive: boolean;
  can_unarchive: boolean;
  can_request_archive: boolean;
  can_delete: boolean;
  can_restore: boolean;
  can_review: boolean;
}

export interface Project {
  id: string;
  title: string;
  description: string;
  objectives: string;
  status: ProjectStatus;
  owner: UserSummary;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  archive_requested_at: string | null;
  archive_request_reason: string | null;
  archived_at: string | null;
  deleted_at: string | null;
  purge_eligible_at: string | null;
  member_count: number;
  supervisors: UserSummary[];
  my_role: MembershipRole | null;
  permissions: ProjectPermissions;
}

export interface ProjectMember {
  id: string;
  user: UserSummary;
  membership_role: MembershipRole;
  membership_status: "active" | "removed";
  joined_at: string;
  removed_at: string | null;
}

export interface ProjectInput {
  title: string;
  description: string;
  objectives: string;
}

const base = "/api/v1/projects";

export const listProjects = async (params: QueryParams = {}) =>
  (await api.get<Page<Project>>(base, { params: cleanParams(params) })).data;

export const getProject = async (id: string) => (await api.get<Project>(`${base}/${id}`)).data;

export const createProject = async (input: ProjectInput) => (await api.post<Project>(base, input)).data;

export const updateProject = async (id: string, input: Partial<ProjectInput>) =>
  (await api.patch<Project>(`${base}/${id}`, input)).data;

export const requestArchive = async (id: string, reason: string) =>
  (await api.post<Project>(`${base}/${id}/archive-request`, { reason })).data;

export const archiveProject = async (id: string) => (await api.post<Project>(`${base}/${id}/archive`)).data;
export const unarchiveProject = async (id: string) => (await api.post<Project>(`${base}/${id}/unarchive`)).data;
export const deleteProject = async (id: string) => (await api.delete<Project>(`${base}/${id}`)).data;
export const restoreProject = async (id: string) => (await api.post<Project>(`${base}/${id}/restore`)).data;
export const purgeProject = async (id: string) =>
  (await api.delete<MessageResponse>(`${base}/${id}/permanent`)).data;
export const transferOwnership = async (id: string, newOwnerId: string) =>
  (await api.post<Project>(`${base}/${id}/transfer-ownership`, { new_owner_id: newOwnerId })).data;

export const listMembers = async (id: string, includeRemoved = false) =>
  (await api.get<ProjectMember[]>(`${base}/${id}/members`, { params: { include_removed: includeRemoved } })).data;

export const addMember = async (id: string, userId: string, role: Exclude<MembershipRole, "owner">) =>
  (await api.post<ProjectMember>(`${base}/${id}/members`, { user_id: userId, membership_role: role })).data;

export const changeMemberRole = async (id: string, userId: string, role: Exclude<MembershipRole, "owner">) =>
  (await api.patch<ProjectMember>(`${base}/${id}/members/${userId}`, { membership_role: role })).data;

export const removeMember = async (id: string, userId: string) =>
  (await api.delete<MessageResponse>(`${base}/${id}/members/${userId}`)).data;
