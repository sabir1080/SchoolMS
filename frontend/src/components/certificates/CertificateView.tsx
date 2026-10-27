import type { Tenant } from "@/lib/api";
import { certificateNo, dateInWords, longDate, pronouns, type Certificate } from "@/lib/certificates";

const TITLES = { character: "Character Certificate", leaving: "School Leaving Certificate", bonafide: "Bonafide Certificate" };

/** A printable certificate (A4 portrait) with the institute's name and a decorative border. */
export function CertificateView({
  certificate,
  tenant,
  institute,
}: {
  certificate: Certificate;
  tenant: Tenant | null | undefined;
  institute?: { address?: string; phone?: string; logo?: string };
}) {
  const d = certificate.data;
  const p = pronouns(d.gender);
  const relation = d.father_name ? `${p.child} of ${d.father_name}` : "";
  const name = <strong className="font-semibold">{d.full_name}</strong>;
  const logo = institute?.logo;
  const conduct = (d.conduct || "good").toLowerCase();

  return (
    <article className="mx-auto max-w-3xl bg-white p-3 text-slate-900 shadow-sm print:max-w-none print:shadow-none">
      <div className="border-4 border-double border-indigo-700 p-8 print:p-10">
        <header className="text-center">
          {/* The logo is a small data URL saved with the institute, so next/image is not needed. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {logo && <img src={logo} alt="" className="mx-auto mb-2 h-16 w-16 object-contain" />}
          <h2 className="text-2xl font-bold tracking-tight">{tenant?.name}</h2>
          {(institute?.address || institute?.phone) && (
            <p className="text-xs text-slate-600">{[institute.address, institute.phone].filter(Boolean).join(" · ")}</p>
          )}
          <p className="mt-4 inline-block border-b-2 border-indigo-700 pb-1 text-xl font-semibold tracking-wide text-indigo-800 uppercase">
            {TITLES[certificate.kind]}
          </p>
        </header>
        <div className="mt-4 flex justify-between text-sm">
          <span>No. {certificateNo(certificate.number)}</span>
          <span>Date: {longDate(certificate.issued_on)}</span>
        </div>

        {certificate.kind === "leaving" ? (
          <div className="mt-6">
            <p className="leading-7">
              Certified that {name}, {relation}, has left this institute on {longDate(d.leaving_date)}. The particulars below are as per
              the school record.
            </p>
            <table className="mt-4 w-full border-collapse text-sm">
              <tbody>
                {(
                  [
                    ["Name of student", d.full_name],
                    ["Father / guardian", d.father_name || "—"],
                    ["Admission no", d.admission_no],
                    ["Date of admission", longDate(d.admission_date)],
                    ["Date of birth", d.date_of_birth ? `${longDate(d.date_of_birth)} (${dateInWords(d.date_of_birth)})` : "—"],
                    ["Class at leaving", d.class_name || "—"],
                    ["Date of leaving", longDate(d.leaving_date)],
                    ["Reason for leaving", d.reason || "—"],
                    ["Conduct", d.conduct || "Good"],
                    ["Remarks", d.remarks || "—"],
                  ] as [string, string][]
                ).map(([k, v]) => (
                  <tr key={k}>
                    <td className="w-48 border border-slate-300 px-3 py-1.5 text-slate-600">{k}</td>
                    <td className="border border-slate-300 px-3 py-1.5 font-medium">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-4 leading-7">We wish {p.him} every success in the future.</p>
          </div>
        ) : certificate.kind === "character" ? (
          <div className="mt-8 space-y-4 text-[15px] leading-8">
            <p>
              This is to certify that {name}, {relation}, Admission No. {d.admission_no}, has been a student of this institute
              {d.admission_date && ` since ${longDate(d.admission_date)}`}
              {d.class_name && ` and is studying in ${d.class_name}`}
              {d.leaving_date && ` till ${longDate(d.leaving_date)}`}.
            </p>
            <p>
              During {p.his} stay, {p.he} bore {/^[aeiou]/i.test(conduct) ? "an" : "a"} <strong>{conduct}</strong> moral character and {p.his} conduct
              was satisfactory. {p.He} took part in the activities of the institute with interest.
            </p>
            {d.remarks && <p>{d.remarks}</p>}
            <p>We wish {p.him} success in life.</p>
          </div>
        ) : (
          <div className="mt-8 space-y-4 text-[15px] leading-8">
            <p>
              This is to certify that {name}, {relation}, is a bonafide student of this institute, studying in{" "}
              <strong>{d.class_name || "—"}</strong>
              {d.roll_number && ` (Roll No. ${d.roll_number})`}
              {d.session_name && ` in the session ${d.session_name}`}. {p.His} admission number is {d.admission_no}.
            </p>
            {d.date_of_birth && (
              <p>
                According to the school record, {p.his} date of birth is {longDate(d.date_of_birth)} ({dateInWords(d.date_of_birth)}).
              </p>
            )}
            <p>This certificate is issued on {p.his} request{d.purpose ? ` for ${d.purpose}` : ""}.</p>
          </div>
        )}

        <footer className="mt-20 grid grid-cols-2 gap-10 text-center text-sm">
          <div className="border-t border-slate-500 pt-1">Class teacher / Office</div>
          <div className="border-t border-slate-500 pt-1">Principal (signature &amp; stamp)</div>
        </footer>
      </div>
    </article>
  );
}
