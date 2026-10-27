import { RESULT_LABEL, ordinal, type ExamResults, type ResultRow } from "@/lib/exams";
import { termsFor } from "@/lib/terms";
import type { Tenant } from "@/lib/api";

/** One student's printable report card (A4 portrait). */
export function ReportCard({ data, row, tenant }: { data: ExamResults; row: ResultRow; tenant: Tenant | null | undefined }) {
  const terms = termsFor(tenant);
  const info: [string, string][] = [
    ["Student", row.full_name],
    ["Father / Guardian", row.father_name || "—"],
    [`${terms.program} - ${terms.section}`, `${data.section.program_name} - ${data.section.name}`],
    ["Roll no", row.roll_number || "—"],
    ["Admission no", row.admission_no],
    ["Session", data.exam.session_name],
  ];
  const att = row.attendance;
  const boxes: [string, string, string?][] = [
    ["Marks", `${row.obtained} / ${row.total}`],
    ["Percentage", row.percentage ? `${row.percentage}%` : "—"],
    ["Grade", row.grade ?? "—"],
    ["Result", RESULT_LABEL[row.result].label, RESULT_LABEL[row.result].tone],
  ];
  if (data.show_position) boxes.push(["Position", row.position ? ordinal(row.position) : "—"]);
  if (att && att.total) boxes.push(["Attendance", att.percentage !== null ? `${att.percentage}%` : "—"]);

  return (
    <article className="report-card mx-auto max-w-3xl rounded-2xl bg-white p-6 text-slate-900 shadow-sm print:max-w-none print:rounded-none print:p-0 print:shadow-none">
      <header className="border-b-2 border-indigo-600 pb-3 text-center">
        <h2 className="text-2xl font-bold tracking-tight">{data.institute.name}</h2>
        {(data.institute.address || data.institute.phone) && (
          <p className="text-xs text-slate-600">{[data.institute.address, data.institute.phone].filter(Boolean).join(" · ")}</p>
        )}
        <p className="mt-2 inline-block rounded-full bg-indigo-600 px-4 py-1 text-sm font-semibold text-white print:border print:border-indigo-600 print:bg-white print:text-indigo-700">
          Report card · {data.exam.name}
        </p>
      </header>

      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
        {info.map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-slate-500">{k}</dt>
            <dd className="font-medium">{v}</dd>
          </div>
        ))}
      </dl>

      <table className="mt-4 w-full border-collapse text-[13px] sm:text-sm">
        <thead>
          <tr className="bg-slate-100 text-left text-xs text-slate-600">
            <th className="border border-slate-200 px-1.5 py-1.5 sm:px-2 font-medium">Subject</th>
            <th className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-right font-medium">Total</th>
            <th className="hidden border border-slate-200 px-1.5 py-1.5 text-right font-medium sm:table-cell sm:px-2 print:table-cell">Pass</th>
            <th className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-right font-medium">Obtained</th>
            <th className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-center font-medium">Grade</th>
            <th className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-center font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {data.papers.map((p, i) => {
            const s = row.subjects[i];
            return (
              <tr key={p.id}>
                <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2 font-medium">{p.subject_name}</td>
                <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-right">{p.total_marks}</td>
                <td className="hidden border border-slate-200 px-1.5 py-1.5 text-right sm:table-cell sm:px-2 print:table-cell">{p.pass_marks}</td>
                <td className={`border border-slate-200 px-1.5 py-1.5 sm:px-2 text-right font-semibold ${s.passed === false ? "text-red-600" : ""}`}>
                  {s.absent ? "Absent" : (s.marks ?? "—")}
                </td>
                <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-center">{s.grade ?? "—"}</td>
                <td className={`border border-slate-200 px-1.5 py-1.5 sm:px-2 text-center text-xs ${s.passed === false ? "text-red-600" : "text-emerald-700"}`}>
                  {s.passed === null ? "—" : s.passed ? "Pass" : "Fail"}
                </td>
              </tr>
            );
          })}
          <tr className="bg-slate-50 font-semibold">
            <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2">Total</td>
            <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-right">{row.total}</td>
            <td className="hidden border border-slate-200 px-1.5 py-1.5 sm:table-cell sm:px-2 print:table-cell" />
            <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-right">{row.obtained}</td>
            <td className="border border-slate-200 px-1.5 py-1.5 sm:px-2 text-center">{row.grade ?? "—"}</td>
            <td className={`border border-slate-200 px-1.5 py-1.5 sm:px-2 text-center text-xs ${RESULT_LABEL[row.result].tone}`}>{RESULT_LABEL[row.result].label}</td>
          </tr>
        </tbody>
      </table>

      <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
        {boxes.map(([k, v, tone]) => (
          <div key={k} className="rounded-xl border border-slate-200 px-2 py-2 text-center">
            <p className="text-[11px] text-slate-500">{k}</p>
            <p className={`text-base font-bold ${tone ?? ""}`}>{v}</p>
          </div>
        ))}
      </div>

      {row.remark && (
        <p className="mt-3 text-sm">
          <span className="text-slate-500">Remarks: </span>
          <span className="font-medium">{row.remark}</span>
          {att && att.total > 0 && (
            <span className="text-slate-500">
              {" "}
              · Attended {att.present + att.late} of {att.total - att.leave} days{att.leave ? ` (${att.leave} on leave)` : ""}
            </span>
          )}
        </p>
      )}

      <p className="mt-3 text-[11px] text-slate-500">
        Grades: {data.grading.map((g) => `${g.name} ${g.min_percentage}%+`).join(" · ")}. Pass marks in each subject: {data.pass_percentage}%.
      </p>

      <footer className="mt-12 grid grid-cols-3 gap-6 text-center text-xs text-slate-600">
        {["Class teacher", "Principal", "Parent / Guardian"].map((who) => (
          <div key={who}>
            <div className="border-t border-slate-400 pt-1">{who}</div>
            {who === "Class teacher" && data.section.class_teacher_name && <div className="text-[11px]">{data.section.class_teacher_name}</div>}
          </div>
        ))}
      </footer>
    </article>
  );
}
