export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const ACCESS_KEY = "sms_access";
const REFRESH_KEY = "sms_refresh";

export type Role = "super_admin" | "admin" | "teacher" | "student" | "parent";

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  institute_type: string;
  country: string;
  currency: string;
  timezone: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: Role;
  tenant: Tenant | null;
}

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(extractMessage(body) ?? `Request failed (${status})`);
  }
}

function extractMessage(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) return String((body as { detail: unknown }).detail);
  return undefined;
}

export const tokens = {
  get access() {
    return typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  const res = await fetch(`${API_URL}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    tokens.clear();
    return false;
  }
  const data = await res.json();
  tokens.set(data.access, data.refresh);
  return true;
}

/** Call the backend API. Adds the JWT and retries once after refreshing an expired token. */
export async function api<T = unknown>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401 && retry && tokens.refresh && (await refreshAccessToken())) {
    return api<T>(path, init, false);
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}
