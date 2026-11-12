import { AxiosError, AxiosHeaders, type AxiosAdapter, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api, { CSRF_ERROR_DETAIL, getErrorMessage, onSessionChanged, onUnauthorized, setCsrfToken } from "../services/api";

type Reply = { status: number; data: unknown };
type Route = (config: InternalAxiosRequestConfig) => Reply;

let routes: Record<string, Route[]>;
let seen: { method: string; url: string; csrf: string | null }[];
const originalAdapter = api.defaults.adapter;

// Fake transport: each "METHOD url" key answers with its queued replies in order.
const adapter: AxiosAdapter = async (config) => {
  const method = (config.method ?? "get").toUpperCase();
  const key = `${method} ${config.url}`;
  seen.push({ method, url: config.url ?? "", csrf: (config.headers.get("X-CSRF-Token") as string | null) ?? null });
  const handler = routes[key]?.shift();
  if (!handler) throw new Error(`Unexpected request ${key}`);
  const { status, data } = handler(config);
  const response = { status, data, statusText: String(status), headers: new AxiosHeaders(), config };
  if (status >= 400) {
    throw new AxiosError(`HTTP ${status}`, String(status), config, undefined, response);
  }
  return response;
};

const csrfRejected: Route = () => ({ status: 403, data: { detail: CSRF_ERROR_DETAIL } });
const me = (id: string, token: string): Route => () => ({ status: 200, data: { id, csrf_token: token } });
const created: Route = () => ({ status: 201, data: { id: "paper-1" } });

beforeEach(() => {
  routes = {};
  seen = [];
  api.defaults.adapter = adapter;
});

afterEach(() => {
  api.defaults.adapter = originalAdapter;
  setCsrfToken(null);
  onUnauthorized(null);
  onSessionChanged(null);
});

describe("CSRF token recovery", () => {
  it("refreshes a stale token from /auth/me and retries the write once", async () => {
    setCsrfToken("stale", "user-1");
    routes["POST /api/v1/research/papers"] = [csrfRejected, created];
    routes["GET /api/v1/auth/me"] = [me("user-1", "fresh")];

    const response = await api.post("/api/v1/research/papers", { title: "x" });

    expect(response.status).toBe(201);
    expect(seen.map((r) => `${r.method} ${r.csrf}`)).toEqual(["POST stale", "GET null", "POST fresh"]);

    // Later writes use the refreshed token straight away.
    routes["PATCH /api/v1/tasks/t1"] = [() => ({ status: 200, data: {} })];
    await api.patch("/api/v1/tasks/t1", {});
    expect(seen.at(-1)?.csrf).toBe("fresh");
  });

  it("does not retry more than once", async () => {
    setCsrfToken("stale", "user-1");
    routes["POST /api/v1/projects"] = [csrfRejected, csrfRejected];
    routes["GET /api/v1/auth/me"] = [me("user-1", "fresh")];

    await expect(api.post("/api/v1/projects", {})).rejects.toMatchObject({ response: { status: 403 } });
    expect(seen.filter((r) => r.method === "POST")).toHaveLength(2);
  });

  it("never replays a change after another account signed in", async () => {
    const changed = vi.fn();
    onSessionChanged(changed);
    setCsrfToken("stale", "user-1");
    routes["POST /api/v1/research/papers"] = [csrfRejected];
    routes["GET /api/v1/auth/me"] = [me("user-2", "other")];

    const error = await api.post("/api/v1/research/papers", {}).catch((e: unknown) => e);

    expect(getErrorMessage(error)).toMatch(/different user in another tab/);
    expect(changed).toHaveBeenCalledWith({ id: "user-2", csrf_token: "other" });
    expect(seen.filter((r) => r.method === "POST")).toHaveLength(1);
  });

  it("asks to save again when the page lost track of the signed-in user", async () => {
    const changed = vi.fn();
    onSessionChanged(changed);
    routes["POST /api/v1/research/papers"] = [csrfRejected];
    routes["GET /api/v1/auth/me"] = [me("user-1", "fresh")];

    const error = await api.post("/api/v1/research/papers", {}).catch((e: unknown) => e);

    expect(getErrorMessage(error)).toMatch(/save again/);
    expect(changed).toHaveBeenCalled();
  });

  it("sends the user to login when the session has ended", async () => {
    const unauthorized = vi.fn();
    onUnauthorized(unauthorized);
    setCsrfToken("stale", "user-1");
    routes["POST /api/v1/research/papers"] = [csrfRejected];
    routes["GET /api/v1/auth/me"] = [() => ({ status: 401, data: { detail: "Authentication required." } })];

    await expect(api.post("/api/v1/research/papers", {})).rejects.toBeInstanceOf(AxiosError);
    expect(unauthorized).toHaveBeenCalled();
  });

  it("leaves other 403 errors alone", async () => {
    setCsrfToken("token", "user-1");
    routes["POST /api/v1/research/papers"] = [() => ({ status: 403, data: { detail: "You cannot add papers." } })];

    const error = await api.post("/api/v1/research/papers", {}).catch((e: unknown) => e);
    expect(getErrorMessage(error)).toBe("You cannot add papers.");
    expect(seen).toHaveLength(1);
  });
});
