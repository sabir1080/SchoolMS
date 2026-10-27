export type StudentStatus = "active" | "left" | "graduated" | "suspended";

export interface Enrollment {
  id: number;
  section: number;
  section_name: string;
  program: number;
  program_name: string;
  session: number;
  session_name: string;
  is_current: boolean;
  roll_number: string;
  enrolled_on: string;
}

export interface GuardianInfo {
  id: number;
  name: string;
  phone: string;
  cnic: string;
  email: string;
  occupation: string;
  address: string;
  username: string | null;
  children: { id: number; full_name: string; admission_no: string }[];
}

export interface StudentListItem {
  id: number;
  admission_no: string;
  first_name: string;
  last_name: string;
  full_name: string;
  gender: string;
  status: StudentStatus;
  current_enrollment: Enrollment | null;
  guardian_name: string | null;
  guardian_phone: string | null;
  has_login: boolean;
}

export interface StudentDetail extends StudentListItem {
  photo: string;
  date_of_birth: string | null;
  id_number: string;
  blood_group: string;
  phone: string;
  email: string;
  address: string;
  admission_date: string;
  previous_school: string;
  notes: string;
  username: string | null;
  enrollments: Enrollment[];
  guardian_links: { relation: string; is_primary: boolean; guardian: GuardianInfo }[];
}

export const GENDERS: [string, string][] = [
  ["male", "Male"],
  ["female", "Female"],
  ["other", "Other"],
];

export const RELATIONS: [string, string][] = [
  ["father", "Father"],
  ["mother", "Mother"],
  ["guardian", "Guardian"],
  ["brother", "Brother"],
  ["sister", "Sister"],
  ["other", "Other"],
];

export const STATUSES: [StudentStatus, string][] = [
  ["active", "Active"],
  ["left", "Left"],
  ["graduated", "Graduated"],
  ["suspended", "Suspended"],
];

export const BLOOD_GROUPS = ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export function label(options: [string, string][], value: string) {
  return options.find(([v]) => v === value)?.[1] ?? value;
}

export function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "Class 5 - A (Roll 7)" */
export function enrollmentText(e: Enrollment | null, sectionWord: string) {
  if (!e) return "Not assigned";
  return `${e.program_name} - ${sectionWord} ${e.section_name}${e.roll_number ? ` (Roll ${e.roll_number})` : ""}`;
}
