import type { Tenant } from "@/lib/api";
import { RESULT_LABEL, ordinal, type CombinedResults, type CombinedRow } from "@/lib/exams";
import { termsFor } from "@/lib/terms";

/** One student's printable annual (combined) report card: each exam's percentage and the weighted total. */
export function CombinedCard({ data, row, tenant }: { data: CombinedResults; row: CombinedRow; tenant: Tenant | null | undefined }) {
  const terms = termsFor(tenant);
  const info: [string, string][] = [
    ["Student", row.full_name],
    ["Father / Guardian", row.father_name || "—"],
    [`${terms.program} - ${terms.section}`, `${data.section.program_name} - ${data.section.name}`],
    ["Roll no", row.roll_number || "—"],
    ["Admission no", row.admission_no],
    ["Session", data.combined.session_name],
  ];
  const att = row.attendance;
  const boxes: [string, string, string?][] = [
    ["Percentage", row.percentage ? `${row.percentage}%` : "—"],
    ["Grade", row.grade ?? "—"],
    ["Result", RESULT_LABEL[row.result].label, RESULT_LABEL[row.result].tone],
  ];
  if (data.show_position) boxes.push(["Position", row.position ? ordinal(row.position) : "—"]);
  if (att && att.total) boxes.push(["Attendance", att.percentage !== null ? `${att.percentage}%` : "—"]);
  const cell = "border border-slate-200 px-1.5 py-1.5 sm:px-2";
  const pct = (v: string | null) => (v === null ? "—" : `${v}%`);

  return (
    <article className="report-card mx-auto max-w-3xl rounded-2xl bg-white p-6 text-slate-900 shadow-sm print:max-w-none print:rounded-none print:p-0 print:shadow-none">
      <header className="border-b-2 border-indigo-600 pb-3 text-center">
        <h2 className="text-2xl font-bold tracking-tight">{data.institute.name}</h2>
        {(data.institute.address || data.institute.phone) && (
          <p className="text-xs text-slate-600">{[data.institute.address, data.institute.phone].filter(Boolean).join(" · ")}</p>
        )}
        <p className="mt-2 inline-block rounded-full bg-indigo-600 px-4 py-1 text-sm font-semibold text-white print:border print:border-indigo-600 print:bg-white print:text-indigo-700">
          {data.combined.name}
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

      <div className="mt-4 overflow-x-auto print:overflow-visible">
        <table className="w-full border-collapse text-[13px] sm:text-sm">
          <thead>
            <tr className="bg-slate-100 text-left text-xs text-slate-600">
              <th className={`${cell} font-medium`}>Subject</th>
              {data.exams.map((e) => (
                <th key={e.id} className={`${cell} text-right font-medium`}>
                  {e.name}
                  <span className="block text-[10px] font-normal">{e.weight}%</span>
                </th>
              ))}
              <th className={`${cell} text-right font-medium`}>Annual</th>
              <th className={`${cell} text-center font-medium`}>Grade</th>
            </tr>
          </thead>
          <tbody>
            {data.subjects.map((subject, i) => {
              const s = row.subjects[i];
              return (
                <tr key={subject.id}>
                  <td className={`${cell} font-medium`}>{subject.name}</td>
                  {s.exams.map((e) => (
                    <td key={e.exam} className={`${cell} text-right text-slate-600`}>
                      {pct(e.percentage)}
                    </td>
                  ))}
                  <td className={`${cell} text-right font-semibold ${s.passed === false ? "text-red-600" : ""}`}>{pct(s.percentage)}</td>
                  <td className={`${cell} text-center`}>{s.grade ?? "—"}</td>
                </tr>
              );
            })}
            <tr className="bg-slate-50 font-semibold">
              <td className={cell}>Overall</td>
              {row.exams.map((e) => (
                <td key={e.exam} className={`${cell} text-right`}>
                  {pct(e.percentage)}
                </td>
              ))}
              <td className={`${cell} text-right`}>{pct(row.percentage)}</td>
              <td className={`${cell} text-center`}>{row.grade ?? "—"}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5">
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
          {row.result === "fail" && <span className="text-red-600"> · Below {data.pass_percentage}% in {row.failed_subjects} subject(s)</span>}
        </p>
      )}
      <p className="mt-3 text-[11px] text-slate-500">
        Annual percentage = {data.exams.map((e) => `${e.name} × ${e.weight}%`).join(" + ")}. A subject is passed at {data.pass_percentage}% or more.
        Grades: {data.grading.map((g) => `${g.name} ${g.min_percentage}%+`).join(" · ")}.
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
