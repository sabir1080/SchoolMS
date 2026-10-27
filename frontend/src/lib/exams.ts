export type ExamStatus = "draft" | "marks_open" | "published";

export interface Exam {
  id: number;
  session: number;
  session_name: string;
  name: string;
  exam_type: string;
  start_date: string | null;
  end_date: string | null;
  status: ExamStatus;
  programs: number[];
  program_names: string[];
  notes: string;
  paper_count: number;
}

export interface Paper {
  id: number;
  program: number;
  program_name: string;
  subject: number;
  subject_name: string;
  total_marks: string;
  pass_marks: string;
  date: string | null;
  start_time: string | null;
}

export interface GradeBand {
  name: string;
  min_percentage: string;
  remark: string;
}

export const EXAM_TYPES: [string, string][] = [
  ["test", "Test"],
  ["term", "Term exam"],
  ["midterm", "Mid-term"],
  ["final", "Final exam"],
  ["other", "Other"],
];

export const EXAM_STATUS: Record<ExamStatus, { label: string; tone: string }> = {
  draft: { label: "Being prepared", tone: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  marks_open: { label: "Marks entry open", tone: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200" },
  published: { label: "Result published", tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" },
};

/** "15 Sep" or "15 Sep 2026". */
export function shortDate(iso: string | null, withYear = false) {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    weekday: withYear ? undefined : "short",
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
  });
}

export function timeText(t: string | null) {
  if (!t) return "";
  const [h, m] = t.split(":").map(Number);
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function marks(value: string) {
  return value.replace(/\.00$/, "");
}
