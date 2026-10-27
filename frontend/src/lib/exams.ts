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

/** "70.50" -> "70.5", "100.00" -> "100". */
export function marks(value: string) {
  return value.includes(".") ? value.replace(/\.?0+$/, "") : value;
}

export interface ProgressSection {
  id: number;
  program: number;
  program_name: string;
  name: string;
  session_name: string;
  student_count: number;
  papers: { id: number; subject_name: string; total_marks: string; entered: number }[];
}

export interface MarksProgress {
  exam: { id: number; name: string; status: ExamStatus; session_name: string };
  can_enter: boolean;
  sections: ProgressSection[];
}

export interface MarksRow {
  student: number;
  admission_no: string;
  full_name: string;
  roll_number: string;
  marks: string | null;
  absent: boolean;
}

export interface MarksSheet {
  exam: { id: number; name: string; status: ExamStatus };
  can_enter: boolean;
  section: { id: number; program_name: string; name: string; session_name: string };
  paper: Paper;
  students: MarksRow[];
}

export type ResultStatus = "pass" | "fail" | "incomplete";

export interface ResultRow {
  student: number;
  full_name: string;
  admission_no: string;
  roll_number: string;
  father_name: string;
  subjects: { paper: number; marks: string | null; absent: boolean; grade: string | null; passed: boolean | null }[];
  obtained: string;
  total: string;
  percentage: string | null;
  grade: string | null;
  remark: string;
  result: ResultStatus;
  failed_subjects: number;
  position: number | null;
  attendance?: { total: number; present: number; late: number; absent: number; leave: number; percentage: number | null };
}

export interface ExamResults {
  exam: { id: number; name: string; status: ExamStatus; exam_type: string; session_name: string; start_date: string | null; end_date: string | null };
  institute: { name: string; address: string; phone: string; email: string };
  section: { id: number; program_name: string; name: string; session_name: string; class_teacher_name: string | null };
  show_position: boolean;
  pass_percentage: number;
  papers: { id: number; subject_name: string; total_marks: string; pass_marks: string }[];
  students: ResultRow[];
  summary: { students: number; passed: number; failed: number; incomplete: number; pass_rate: string | null; average: string | null; highest: string | null };
  grading: { name: string; min_percentage: string; remark: string }[];
}

export const RESULT_LABEL: Record<ResultStatus, { label: string; tone: string }> = {
  pass: { label: "Pass", tone: "text-emerald-700 dark:text-emerald-400" },
  fail: { label: "Fail", tone: "text-red-600 dark:text-red-400" },
  incomplete: { label: "Incomplete", tone: "text-slate-500" },
};

/** 1 -> "1st", 2 -> "2nd", 11 -> "11th", 22 -> "22nd". */
export function ordinal(n: number) {
  const teen = n % 100 >= 11 && n % 100 <= 13;
  const suffix = teen ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th";
  return `${n}${suffix}`;
}

export interface Combined {
  id: number;
  session: number;
  session_name: string;
  name: string;
  status: "draft" | "published";
  components: { exam: number; exam_name: string; exam_status: ExamStatus; weight: string }[];
}

export const COMBINED_STATUS: Record<Combined["status"], { label: string; tone: string }> = {
  draft: EXAM_STATUS.draft,
  published: { label: "Published", tone: EXAM_STATUS.published.tone },
};

export interface CombinedRow {
  student: number;
  full_name: string;
  admission_no: string;
  roll_number: string;
  father_name: string;
  exams: { exam: number; percentage: string | null }[];
  subjects: {
    subject: number;
    percentage: string | null;
    grade: string | null;
    passed: boolean | null;
    exams: { exam: number; percentage: string | null }[];
  }[];
  percentage: string | null;
  grade: string | null;
  remark: string;
  result: ResultStatus;
  failed_subjects: number;
  position: number | null;
  attendance?: ResultRow["attendance"];
}

export type ResultSummaryData = ExamResults["summary"];

export interface CombinedResults {
  combined: { id: number; name: string; status: Combined["status"]; session_name: string };
  institute: ExamResults["institute"];
  section: ExamResults["section"];
  show_position: boolean;
  pass_percentage: number;
  exams: { id: number; name: string; weight: string }[];
  subjects: { id: number; name: string }[];
  students: CombinedRow[];
  summary: ResultSummaryData;
  grading: ExamResults["grading"];
  sections: { id: number; program: number; program_name: string; name: string }[];
}

export interface MyResults {
  exams: ExamResults[];
  combined: CombinedResults[];
}
