import type { Role, SubscriptionStatus } from "./api";

export interface NavItem {
  label: string;
  href: string;
  /** Plan feature the page needs; the item is hidden when the institute's plan lacks it. */
  feature?: string;
}

/** Menu per role. New feature modules add their entries here. */
const ACCOUNT: NavItem = { label: "Change password", href: "/account" };
const HELP: NavItem = { label: "Help & manual", href: "/manual" };

export const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  super_admin: [
    { label: "Overview", href: "/platform/overview" },
    { label: "Institutes", href: "/platform/tenants" },
    { label: "Business details", href: "/platform/business" },
    { label: "Owner guide", href: "/platform/guide" },
    ACCOUNT,
  ],
  admin: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Students", href: "/students", feature: "students" },
    { label: "Admissions", href: "/admissions", feature: "admissions" },
    { label: "Attendance", href: "/attendance", feature: "attendance" },
    { label: "Timetable", href: "/timetable", feature: "timetable" },
    { label: "Homework", href: "/homework", feature: "homework" },
    { label: "Exams", href: "/exams", feature: "exams" },
    { label: "Fees", href: "/fees", feature: "fees" },
    { label: "Staff & payroll", href: "/payroll", feature: "payroll" },
    { label: "Messages", href: "/messages", feature: "sms_alerts" },
    { label: "Reports", href: "/reports", feature: "reports" },
    { label: "Certificates", href: "/certificates", feature: "certificates" },
    { label: "Academic setup", href: "/academics", feature: "academics" },
    { label: "Users", href: "/users" },
    { label: "Recycle bin", href: "/recycle-bin" },
    { label: "Institute settings", href: "/settings" },
    { label: "Plan & Billing", href: "/billing" },
    HELP,
    ACCOUNT,
  ],
  teacher: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Attendance", href: "/attendance", feature: "attendance" },
    { label: "Timetable", href: "/timetable", feature: "timetable" },
    { label: "Homework", href: "/homework", feature: "homework" },
    { label: "Exams", href: "/exams", feature: "exams" },
    { label: "Students", href: "/students", feature: "students" },
    { label: "My salary slips", href: "/my-payslips", feature: "payroll" },
    HELP,
    ACCOUNT,
  ],
  student: [{ label: "Dashboard", href: "/dashboard" }, HELP, ACCOUNT],
  parent: [{ label: "Dashboard", href: "/dashboard" }, HELP, ACCOUNT],
};

/** Pages that stay open after an institute's subscription expires. */
export const ALWAYS_OPEN = ["/billing", "/agreement", "/account", "/manual"];

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
