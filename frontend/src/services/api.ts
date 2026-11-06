import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// The CSRF token is returned by /auth/login and /auth/me and kept in
// memory only (never in localStorage).
let csrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

api.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toUpperCase();

  if (csrfToken && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? "";

    // An expired or revoked session anywhere in the app returns the
    // user to the login page.
    if (
      error.response?.status === 401 &&
      !url.includes("/auth/login") &&
      !url.includes("/auth/me")
    ) {
      unauthorizedHandler?.();
    }

    return Promise.reject(error);
  }
);

interface ValidationIssue {
  msg?: string;
  loc?: (string | number)[];
}

// Turn any API error into a readable sentence.
export function getErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again."
): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return (detail as ValidationIssue[])
        .map((issue) => {
          const field = issue.loc?.filter((part) => part !== "body").join(".");
          const message = (issue.msg ?? "").replace(/^Value error, /, "");
          return field ? `${field}: ${message}` : message;
        })
        .join(" ");
    }

    if (error.response?.status === 429) {
      return "Too many attempts. Please wait and try again.";
    }

    if (!error.response) {
      return "Cannot reach the Prism Desk server.";
    }
  }

  return fallback;
}

export default api;
