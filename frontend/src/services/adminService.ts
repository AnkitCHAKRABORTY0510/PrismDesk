import api from "./api";
import { cleanParams, type Page } from "./types";

export type RoleName = "Administrator" | "Professor" | "Student" | "Guest";
export type AccountStatus = "pending" | "approved" | "rejected" | "suspended";

// Pending user information returned by FastAPI.
export interface PendingUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  account_status: string;
  created_at: string;
}

// Administrator action response.
export interface AdminActionResponse {
  message: string;
  user_id: string;
  username: string;
  account_status: string;
  assigned_role?: string | null;
  roles: string[];
}

export interface ManagedUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  account_status: AccountStatus;
  roles: RoleName[];
  created_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  suspended_at: string | null;
}

export interface UserFilters {
  search?: string;
  account_status?: string;
  role_name?: string;
  page?: number;
  page_size?: number;
}

// Retrieve pending registrations.
export const getPendingUsers = async (): Promise<PendingUser[]> => {
  const response = await api.get<PendingUser[]>("/api/v1/admin/pending-users");
  return response.data;
};

// Approve a user and assign a role.
export const approveUser = async (
  userId: string,
  roleName: "Student" | "Professor" | "Guest"
): Promise<AdminActionResponse> => {
  const response = await api.post<AdminActionResponse>(
    `/api/v1/admin/users/${userId}/approve`,
    { role_name: roleName }
  );
  return response.data;
};

// Reject a pending registration.
export const rejectUser = async (userId: string): Promise<AdminActionResponse> => {
  const response = await api.post<AdminActionResponse>(`/api/v1/admin/users/${userId}/reject`);
  return response.data;
};

export const getAllUsers = async (filters: UserFilters = {}): Promise<Page<ManagedUser>> => {
  const response = await api.get<Page<ManagedUser>>("/api/v1/admin/users", {
    params: cleanParams({ ...filters }),
  });
  return response.data;
};

export const suspendUser = async (userId: string): Promise<AdminActionResponse> => {
  const response = await api.patch<AdminActionResponse>(`/api/v1/admin/users/${userId}/suspend`);
  return response.data;
};

export const reactivateUser = async (userId: string): Promise<AdminActionResponse> => {
  const response = await api.patch<AdminActionResponse>(`/api/v1/admin/users/${userId}/reactivate`);
  return response.data;
};

export const assignRole = async (userId: string, roleName: RoleName) =>
  (await api.post<AdminActionResponse>(`/api/v1/admin/users/${userId}/roles`, { role_name: roleName })).data;

export const removeRole = async (userId: string, roleName: RoleName) =>
  (await api.delete<AdminActionResponse>(`/api/v1/admin/users/${userId}/roles/${roleName}`)).data;
