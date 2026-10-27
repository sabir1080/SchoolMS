import type { ResultSummaryData } from "@/lib/exams";

/** Students, passed, failed, pass rate, average and highest of a class result. */
export function ResultSummary({ summary: s }: { summary: ResultSummaryData }) {
  const tiles: [string, string, string?][] = [
    ["Students", String(s.students)],
    ["Passed", String(s.passed), "text-emerald-700 dark:text-emerald-400"],
    ["Failed", String(s.failed), s.failed ? "text-red-600 dark:text-red-400" : undefined],
    ["Pass rate", s.pass_rate ? `${s.pass_rate}%` : "—"],
    ["Average", s.average ? `${s.average}%` : "—"],
    ["Highest", s.highest ? `${s.highest}%` : "—"],
  ];
  return (
    <div className="print:hidden">
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {tiles.map(([label, value, tone]) => (
          <div key={label} className="rounded-2xl bg-white p-3 shadow-sm dark:bg-slate-900">
            <p className="text-xs text-slate-500">{label}</p>
            <p className={`text-xl font-semibold ${tone ?? ""}`}>{value}</p>
          </div>
        ))}
      </div>
      {s.incomplete > 0 && (
        <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
          {s.incomplete} {s.incomplete === 1 ? "student has" : "students have"} marks missing in some subjects (shown as Incomplete).
        </p>
      )}
    </div>
  );
}
