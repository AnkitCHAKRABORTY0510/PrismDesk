export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserSummary {
  id: string;
  username: string;
  full_name: string;
  roles: string[];
}

export interface MessageResponse {
  message: string;
}

export type QueryParams = Record<string, string | number | boolean | undefined | null>;

// Drop empty filter values so they are not sent as "" to the API.
export function cleanParams(params: QueryParams): QueryParams {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== undefined && value !== null && value !== ""
    )
  );
}
