import type { Envelope } from "./types";

export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/1";

export class ApiError extends Error {
  status: number;
  code: string;
  data: Record<string, any>;
  constructor(status: number, code: string, message: string, data: Record<string, any> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.data = data;
  }
  /** Server validation: {field: message} for every failing field. */
  get fields(): Record<string, string> {
    const raw = this.data?.fields;
    return raw && typeof raw === "object" ? (raw as Record<string, string>) : {};
  }
}

// --- Staff session (sessionStorage: cleared when the tab closes; wiped on sign-out) ---------------
const ACCESS = "cq.access";
const REFRESH = "cq.refresh";
const store = {
  get(key: string): string | null {
    try {
      return window.sessionStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string | null) {
    try {
      if (value == null) window.sessionStorage.removeItem(key);
      else window.sessionStorage.setItem(key, value);
    } catch {
      /* storage unavailable: the session then lives only until reload */
    }
  },
};
let memoryAccess: string | null = null;
export const session = {
  access: (): string | null => memoryAccess ?? store.get(ACCESS),
  refresh: (): string | null => store.get(REFRESH),
  set(access: string, refresh?: string) {
    memoryAccess = access;
    store.set(ACCESS, access);
    if (refresh) store.set(REFRESH, refresh);
  },
  clear() {
    memoryAccess = null;
    store.set(ACCESS, null);
    store.set(REFRESH, null);
  },
};

type Query = Record<string, string | number | boolean | null | undefined>;
interface Options {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  query?: Query;
  auth?: boolean;
}

function url(path: string, query?: Query): string {
  const qs = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const s = qs.toString();
  return `${API_URL}/${path}${s ? `?${s}` : ""}`;
}

let refreshing: Promise<boolean> | null = null;
async function tryRefresh(): Promise<boolean> {
  const refresh = session.refresh();
  if (!refresh) return false;
  refreshing ??= fetch(url("auth/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      const body = (await r.json()) as Envelope<{ access: string; refresh?: string }>;
      session.set(body.data.access, body.data.refresh);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function send(path: string, opts: Options, retry: boolean): Promise<Response> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const token = opts.auth === false ? null : session.access();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(url(path, opts.query), {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network", "Can't reach the server — check your connection.");
  }
  if (res.status === 401 && opts.auth !== false && retry && (await tryRefresh())) return send(path, opts, false);
  return res;
}

async function fail(res: Response): Promise<never> {
  let body: any = {};
  try {
    body = await res.json();
  } catch {
    /* non-JSON error */
  }
  throw new ApiError(res.status, body.code ?? "error", body.message ?? "Something went wrong. Try again.", body.data ?? {});
}

export async function request<T>(path: string, opts: Options = {}): Promise<Envelope<T>> {
  const res = await send(path, opts, true);
  if (!res.ok) return fail(res);
  return (await res.json()) as Envelope<T>;
}

export const api = {
  get: <T>(path: string, query?: Query, auth = true) => request<T>(path, { query, auth }),
  post: <T>(path: string, body?: unknown, opts: { query?: Query; auth?: boolean } = {}) =>
    request<T>(path, { method: "POST", body: body ?? {}, ...opts }),
  patch: <T>(path: string, body: unknown, query?: Query) => request<T>(path, { method: "PATCH", body, query }),
};

/** Download a CSV with the staff token; returns the blob and the server's file name. */
export async function download(path: string, query?: Query): Promise<{ blob: Blob; filename: string }> {
  const res = await send(path, { query }, true);
  if (!res.ok) return fail(res);
  const match = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "");
  return { blob: await res.blob(), filename: match?.[1] ?? "counselqueue.csv" };
}
