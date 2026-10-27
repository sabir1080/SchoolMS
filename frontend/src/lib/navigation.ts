import type { Role, SubscriptionStatus } from "./api";

export interface NavItem {
  label: string;
  href: string;
}

/** Menu per role. New feature modules add their entries here. */
export const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  super_admin: [{ label: "Institutes", href: "/platform/tenants" }],
  admin: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Users", href: "/users" },
    { label: "Plan & Billing", href: "/billing" },
  ],
  teacher: [{ label: "Dashboard", href: "/dashboard" }],
  student: [{ label: "Dashboard", href: "/dashboard" }],
  parent: [{ label: "Dashboard", href: "/dashboard" }],
};

export const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super Admin",
  admin: "Institute Admin",
  teacher: "Teacher",
  student: "Student",
  parent: "Parent",
};

export const STATUS_LABELS: Record<SubscriptionStatus, string> = {
  trialing: "Free trial",
  active: "Active",
  past_due: "Payment overdue",
  expired: "Expired",
  cancelled: "Cancelled",
};

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
