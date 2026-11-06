import api from "./api";

// User information returned by the backend.
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  roles: string[];
  capabilities: string[];
  csrf_token: string | null;
  message: string;
}

// Login request.
export interface LoginCredentials {
  identifier: string;
  password: string;
}

// Registration request.
export interface RegisterData {
  username: string;
  email: string;
  full_name: string;
  password: string;
}

// Login API.
export const loginUser = async (
  credentials: LoginCredentials
): Promise<User> => {
  const response = await api.post<User>(
    "/api/v1/auth/login",
    credentials
  );

  return response.data;
};

// Get currently authenticated user.
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get<User>(
    "/api/v1/auth/me"
  );

  return response.data;
};

// Logout API.
export const logoutUser = async (): Promise<void> => {
  await api.post("/api/v1/auth/logout");
};

// Registration API.
export const registerUser = async (
  userData: RegisterData
) => {
  const response = await api.post(
    "/api/v1/auth/register",
    userData
  );

  return response.data;
};
