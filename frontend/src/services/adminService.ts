import api from "./api";

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
}

// Retrieve pending registrations.
export const getPendingUsers = async (): Promise<PendingUser[]> => {
  const response = await api.get<PendingUser[]>(
    "/api/v1/admin/pending-users"
  );

  return response.data;
};

// Approve a user and assign a role.
export const approveUser = async (
  userId: string,
  roleName: "Student" | "Professor" | "Guest"
): Promise<AdminActionResponse> => {
  const response = await api.post<AdminActionResponse>(
    `/api/v1/admin/users/${userId}/approve`,
    {
      role_name: roleName,
    }
  );

  return response.data;
};

// Reject a pending registration.
export const rejectUser = async (
  userId: string
): Promise<AdminActionResponse> => {
  const response = await api.post<AdminActionResponse>(
    `/api/v1/admin/users/${userId}/reject`
  );

  return response.data;
};

export interface ManagedUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  account_status: "pending" | "approved" | "rejected" | "suspended";
  roles: string[];
  created_at: string;
}

export interface UserFilters {
  search?: string;
  account_status?: string;
  role_name?: string;
}

export const getAllUsers = async (
  filters: UserFilters = {}
): Promise<ManagedUser[]> => {
  const response = await api.get<ManagedUser[]>(
    "/api/v1/admin/users",
    {
      params: filters,
    }
  );

  return response.data;
};

export const suspendUser = async (
  userId: string
): Promise<AdminActionResponse> => {
  const response = await api.patch<AdminActionResponse>(
    `/api/v1/admin/users/${userId}/suspend`
  );

  return response.data;
};

export const reactivateUser = async (
  userId: string
): Promise<AdminActionResponse> => {
  const response = await api.patch<AdminActionResponse>(
    `/api/v1/admin/users/${userId}/reactivate`
  );

  return response.data;
};