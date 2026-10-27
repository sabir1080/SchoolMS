import { label, STATUSES, type StudentStatus } from "@/lib/students";

const TONES: Record<StudentStatus, string> = {
  active: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  left: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  graduated: "bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  suspended: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export function StatusBadge({ status }: { status: StudentStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TONES[status]}`}>
      {label(STATUSES, status)}
    </span>
  );
}
