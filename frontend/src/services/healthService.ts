import api from "./api";

export interface HealthResponse {
  application: string;
  status: string;
}

export interface DatabaseHealthResponse {
  application: string;
  database: string;
  status: string;
}

export const getBackendHealth = async (): Promise<HealthResponse> => {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
};

export const getDatabaseHealth =
  async (): Promise<DatabaseHealthResponse> => {
    const response = await api.get<DatabaseHealthResponse>(
      "/health/database"
    );
    return response.data;
  };
