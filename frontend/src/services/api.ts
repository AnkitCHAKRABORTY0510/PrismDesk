import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// The CSRF token is returned by /auth/login and /auth/me and kept in
// memory only (never in localStorage). It is a hash of the HttpOnly
// session cookie, so it goes stale when that cookie changes behind this
// page (signing in again in another tab) and is lost if this module is
// reloaded by Vite during development. A write rejected for its CSRF
// token therefore refreshes the token from /auth/me and is retried once,
// but only while the same user is still signed in.
let csrfToken: string | null = null;
let csrfUserId: string | null = null;
let unauthorizedHandler: (() => void) | null = null;
let sessionChangedHandler: ((user: SessionUser) => void) | null = null;

export const CSRF_ERROR_DETAIL = "Missing or invalid CSRF token.";
const ME_URL = "/api/v1/auth/me";
const SAFE_METHODS = ["GET", "HEAD", "OPTIONS"];

/** The parts of /auth/me this module needs. */
export interface SessionUser {
  id: string;
  csrf_token: string | null;
}

type RetriableConfig = InternalAxiosRequestConfig & { _csrfRetried?: boolean };

export function setCsrfToken(token: string | null, userId: string | null = null) {
  csrfToken = token;
  csrfUserId = token ? userId : null;
}

export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

/** Called when the browser is now signed in as a different user (another tab). */
export function onSessionChanged(handler: ((user: SessionUser) => void) | null) {
  sessionChangedHandler = handler;
}

api.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toUpperCase();

  if (csrfToken && !SAFE_METHODS.includes(method)) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }

  return config;
});

// Concurrent failures share one /auth/me call.
let refreshing: Promise<SessionUser | null> | null = null;

function fetchSession(): Promise<SessionUser | null> {
  refreshing ??= api
    .get<SessionUser>(ME_URL)
    .then((response) => response.data)
    .catch(() => null)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

function isCsrfFailure(error: AxiosError): boolean {
  const data = error.response?.data as { detail?: unknown } | undefined;
  return error.response?.status === 403 && data?.detail === CSRF_ERROR_DETAIL;
}

async function retryWithFreshCsrf(error: AxiosError, config: RetriableConfig) {
  const session = await fetchSession();

  if (!session?.csrf_token) {
    // The session itself is gone: back to the login page.
    unauthorizedHandler?.();
    return Promise.reject(error);
  }

  if (session.id !== csrfUserId) {
    // Another account signed in from this browser, or this page no longer
    // knows who it acted for. Never replay the change under an identity
    // the user did not see: reload the session and ask them to retry.
    sessionChangedHandler?.(session);
    (error.response as { data: unknown }).data = {
      detail: csrfUserId
        ? "You signed in as a different user in another tab, so this change was not saved. Reload the page to continue."
        : "Your session was refreshed. Check the form and save again.",
    };
    return Promise.reject(error);
  }

  setCsrfToken(session.csrf_token, session.id);
  config._csrfRetried = true;
  return api.request(config);
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const url = config?.url ?? "";

    if (config && !config._csrfRetried && isCsrfFailure(error)) {
      return retryWithFreshCsrf(error, config);
    }

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
