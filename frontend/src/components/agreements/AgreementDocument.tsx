import type { Agreement, AgreementPreview } from "@/lib/agreements";
import { AGREEMENT_TONE } from "@/lib/agreements";
import { formatDate } from "@/lib/navigation";

function dateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
}

/** A signed agreement (or a preview of one) as a printable document. */
export function AgreementDocument({ agreement, preview }: { agreement?: Agreement; preview?: AgreementPreview }) {
  const doc = agreement ?? preview!;
  const { provider, schedule } = doc;
  const isTrial = doc.kind === "trial";
  const title = isTrial ? "Free Trial Agreement" : "Subscription Agreement";

  return (
    <article className="mx-auto max-w-3xl rounded-2xl bg-white p-6 text-slate-900 shadow-sm print:max-w-none print:rounded-none print:p-0 print:shadow-none">
      <header className="border-b-2 border-brand-600 pb-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
            <p className="text-xs text-slate-500">
              SchoolMS · version {doc.version}
              {agreement && ` · No. ${agreement.number}`}
            </p>
          </div>
          {agreement ? (
            <span className={`rounded-full px-3 py-1 text-xs font-medium print:border print:border-slate-300 ${AGREEMENT_TONE[agreement.status]}`}>
              {agreement.status_label}
            </span>
          ) : (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">Preview — not signed</span>
          )}
        </div>
      </header>

      <section className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">Service provider</p>
          <p className="font-semibold">{provider.business_name}</p>
          {provider.owner_name && <p>{provider.owner_name}</p>}
          {provider.address && <p className="text-slate-600">{provider.address}</p>}
          {(provider.phone || provider.email) && <p className="text-slate-600">{[provider.phone, provider.email].filter(Boolean).join(" · ")}</p>}
        </div>
        <div>
          <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">Institute</p>
          {agreement ? (
            <>
              <p className="font-semibold">{agreement.institute_legal_name}</p>
              {agreement.institute_address && <p className="text-slate-600">{agreement.institute_address}</p>}
              <p className="text-slate-600">Institute code: {agreement.institute_code}</p>
            </>
          ) : (
            <p className="text-slate-600">The institute named in the signature below (“the Institute”).</p>
          )}
        </div>
      </section>

      {!isTrial && (
        <section className="mt-5">
          <h3 className="text-sm font-semibold">Schedule</h3>
          <table className="mt-2 w-full border-collapse text-sm">
            <tbody>
              {(
                [
                  ["Plan", schedule.plan],
                  ["Period", schedule.cycle_label],
                  ["Fee per period", schedule.price],
                  ["Active students", String(schedule.students_limit ?? "")],
                  ["Staff logins", String(schedule.staff_limit ?? "")],
                  ...(agreement?.period_start && agreement.period_end
                    ? [["Paid period", `${formatDate(agreement.period_start)} – ${formatDate(agreement.period_end)}`]]
                    : []),
                ] as [string, string | undefined][]
              ).map(([k, v]) => (
                <tr key={k}>
                  <td className="w-40 border border-slate-200 px-3 py-1.5 text-slate-500">{k}</td>
                  <td className="border border-slate-200 px-3 py-1.5 font-medium">{v}</td>
                </tr>
              ))}
              <tr>
                <td className="border border-slate-200 px-3 py-1.5 align-top text-slate-500">Included</td>
                <td className="border border-slate-200 px-3 py-1.5 text-xs">{schedule.features?.join(" · ")}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}

      <section className="mt-5 space-y-3">
        {doc.sections.map((s) => (
          <div key={s.heading} className="break-inside-avoid">
            <h3 className="text-sm font-semibold">{s.heading}</h3>
            <p className="mt-0.5 text-sm leading-relaxed text-slate-700">{s.body}</p>
          </div>
        ))}
      </section>

      {agreement && (
        <section className="mt-6 grid gap-4 border-t border-slate-200 pt-4 text-sm sm:grid-cols-2 print:break-inside-avoid">
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">Signed for the Institute</p>
            <p className="mt-1 font-[cursive] text-xl text-brand-800">{agreement.signature}</p>
            <p className="font-medium">
              {agreement.signer_name}
              {agreement.signer_designation && `, ${agreement.signer_designation}`}
            </p>
            {agreement.signer_cnic && <p className="text-slate-600">CNIC {agreement.signer_cnic}</p>}
            {agreement.signer_phone && <p className="text-slate-600">{agreement.signer_phone}</p>}
            <p className="mt-1 text-xs text-slate-500">
              Signed electronically on {dateTime(agreement.signed_at)}
              {agreement.ip_address && ` from ${agreement.ip_address}`}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">For {provider.business_name}</p>
            {agreement.kind === "trial" ? (
              <p className="mt-1 text-slate-600">Free trial — no payment due.</p>
            ) : agreement.activated_at ? (
              <>
                <p className="mt-1 font-medium">Payment received and subscription activated</p>
                <p className="text-slate-600">
                  {agreement.currency} {Number(agreement.amount).toLocaleString()} · {agreement.payment_method}
                  {agreement.payment_reference_recorded && ` · ref. ${agreement.payment_reference_recorded}`}
                </p>
                <p className="text-xs text-slate-500">Activated on {dateTime(agreement.activated_at)}</p>
              </>
            ) : (
              <p className="mt-1 text-amber-700">Waiting for payment. The subscription starts when the payment is recorded.</p>
            )}
          </div>
        </section>
      )}
    </article>
  );
}
