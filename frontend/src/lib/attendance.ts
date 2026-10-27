export type AttendanceStatus = "present" | "absent" | "leave" | "late";

export interface Summary {
  present: number;
  absent: number;
  leave: number;
  late: number;
  total: number;
  percentage: number | null;
}

export interface SectionInfo {
  id: number;
  program_name: string;
  name: string;
  session_name: string;
}

export interface MySection extends SectionInfo {
  class_teacher_name: string | null;
  student_count: number;
  marked_today: boolean;
}

export interface StudentAttendance {
  student: number;
  full_name: string;
  month: string;
  records: { date: string; status: AttendanceStatus; remark: string }[];
  month_summary: Summary;
  session_name: string | null;
  session_summary: Summary;
  today: AttendanceStatus | null;
}

export const STATUS_OPTIONS: { value: AttendanceStatus; label: string; short: string; on: string; dot: string }[] = [
  { value: "present", label: "Present", short: "P", on: "bg-emerald-600 text-white border-emerald-600", dot: "bg-emerald-500" },
  { value: "absent", label: "Absent", short: "A", on: "bg-red-600 text-white border-red-600", dot: "bg-red-500" },
  { value: "leave", label: "Leave", short: "L", on: "bg-sky-600 text-white border-sky-600", dot: "bg-sky-500" },
  { value: "late", label: "Late", short: "Lt", on: "bg-amber-500 text-white border-amber-500", dot: "bg-amber-500" },
];

export function statusInfo(status: AttendanceStatus | null | undefined) {
  return STATUS_OPTIONS.find((s) => s.value === status);
}

export function percentText(summary: Summary) {
  return summary.percentage === null ? "—" : `${summary.percentage}%`;
}

/** Colour for an attendance percentage: green 90+, amber 75+, red below. */
export function percentTone(p: number | null) {
  if (p === null) return "text-slate-500";
  if (p >= 90) return "text-emerald-600";
  if (p >= 75) return "text-amber-600";
  return "text-red-600";
}

export function sectionText(s: SectionInfo, sectionWord: string) {
  return `${s.program_name} - ${sectionWord} ${s.name}`;
}

/** Today's date (YYYY-MM-DD) and month (YYYY-MM) on this device. */
export function localToday() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
