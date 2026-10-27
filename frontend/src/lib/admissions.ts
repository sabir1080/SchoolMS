import type { Brand } from "./brand";

export type ApplicationStatus = "new" | "approved" | "rejected";

export interface Application {
  id: number;
  number: number;
  status: ApplicationStatus;
  status_label: string;
  full_name: string;
  first_name: string;
  last_name: string;
  gender: string;
  date_of_birth: string | null;
  program: number | null;
  program_name: string | null;
  previous_school: string;
  address: string;
  guardian_name: string;
  guardian_relation: string;
  guardian_phone: string;
  guardian_email: string;
  guardian_cnic: string;
  message: string;
  admin_note: string;
  student: number | null;
  created_at: string;
  decided_at: string | null;
  decided_by_name: string | null;
}

export interface PublicForm {
  name: string;
  slug: string;
  institute_type: string;
  address: string;
  phone: string;
  brand: Brand;
  open: boolean;
  programs: { id: number; name: string }[];
}

export const APPLICATION_TABS: [ApplicationStatus, string][] = [
  ["new", "New"],
  ["approved", "Admitted"],
  ["rejected", "Not admitted"],
];

export function applicationNo(n: number) {
  return `APP-${String(n).padStart(4, "0")}`;
}

/** The public form's address for an institute (works on any host the app is served from). */
export function applyLink(code: string) {
  return `${typeof window === "undefined" ? "" : window.location.origin}/apply/?code=${encodeURIComponent(code)}`;
}
