import api from "./api";
import { cleanParams, type UserSummary } from "./types";

export const searchDirectory = async (search: string, roleName?: string) =>
  (
    await api.get<UserSummary[]>("/api/v1/users/directory", {
      params: cleanParams({ search, role_name: roleName, limit: 15 }),
    })
  ).data;
