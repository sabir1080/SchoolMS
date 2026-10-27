import type { Brand } from "./brand";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const ACCESS_KEY = "sms_access";
const REFRESH_KEY = "sms_refresh";
const INSTITUTE_KEY = "sms_institute";

export type Role = "super_admin" | "admin" | "teacher" | "student" | "parent";

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  institute_type: string;
  country: string;
  currency: string;
  timezone: string;
  password_policy: PasswordPolicy;
  program_label: string;
  section_label: string;
  working_days: string;
  brand?: Brand;
}

export type PasswordPolicy = "easy" | "standard" | "strong";

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

export interface PlanPrice {
  currency: string;
  billing_cycle: "monthly" | "yearly";
  amount: string;
}

export interface Plan {
  id: number;
  code: string;
  name: string;
  description: string;
  max_students: number | null;
  max_staff: number | null;
  features: string[];
  feature_labels: string[];
  prices: PlanPrice[];
}

export type SubscriptionStatus = "trialing" | "active" | "past_due" | "expired" | "cancelled";

export interface Subscription {
  plan: Plan;
  status: SubscriptionStatus;
  effective_status: SubscriptionStatus;
  is_usable: boolean;
  billing_cycle: "monthly" | "yearly";
  current_period_start: string;
  current_period_end: string;
  days_left: number;
  usage: { students: number; staff: number };
}

/** Institute picked on the login screen, remembered on this device. */
export interface SavedInstitute {
  name: string;
  slug: string;
  brand?: Brand;
  admissions_open?: boolean;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
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

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export const tokens = {
  get access() {
    return storage()?.getItem(ACCESS_KEY) ?? null;
  },
  get refresh() {
    return storage()?.getItem(REFRESH_KEY) ?? null;
  },
  set(access: string, refresh?: string) {
    storage()?.setItem(ACCESS_KEY, access);
    if (refresh) storage()?.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    storage()?.removeItem(ACCESS_KEY);
    storage()?.removeItem(REFRESH_KEY);
  },
};

export const savedInstitute = {
  get(): SavedInstitute | null {
    try {
      return JSON.parse(storage()?.getItem(INSTITUTE_KEY) ?? "null");
    } catch {
      return null;
    }
  },
  set(institute: SavedInstitute) {
    storage()?.setItem(INSTITUTE_KEY, JSON.stringify(institute));
  },
  clear() {
    storage()?.removeItem(INSTITUTE_KEY);
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

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, { detail: "Cannot reach the server. Check your internet connection and try again." });
  }
  if (res.status === 401 && retry && tokens.refresh && (await refreshAccessToken())) {
    return api<T>(path, init, false);
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

/** Download a file from the API (with the JWT) and save it on the device. */
export async function downloadFile(path: string, fallbackName: string, retry = true): Promise<void> {
  const headers = new Headers();
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { headers });
  } catch {
    throw new ApiError(0, { detail: "Cannot reach the server. Check your internet connection and try again." });
  }
  if (res.status === 401 && retry && tokens.refresh && (await refreshAccessToken())) return downloadFile(path, fallbackName, false);
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

export function formatMoney(amount: string | number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(
      Number(amount),
    );
  } catch {
    return `${currency} ${amount}`;
  }
}

/** Fetch every row of a paginated list endpoint (up to 500). */
export async function apiList<T>(path: string): Promise<T[]> {
  const sep = path.includes("?") ? "&" : "?";
  const data = await api<{ results: T[] } | T[]>(`${path}${sep}page_size=500`);
  return Array.isArray(data) ? data : data.results;
}
