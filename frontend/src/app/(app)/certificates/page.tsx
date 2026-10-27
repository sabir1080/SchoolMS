"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api, apiList } from "@/lib/api";
import { KINDS, certificateNo, longDate, type Certificate, type CertificateKind } from "@/lib/certificates";
import { isoDay } from "@/lib/homework";

interface StudentHit {
  id: number;
  full_name: string;
  admission_no: string;
  status: string;
  current_enrollment: { program_name: string; section_name: string } | null;
}

export default function CertificatesPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<StudentHit[]>([]);
  const [student, setStudent] = useState<StudentHit | null>(null);
  const [kind, setKind] = useState<CertificateKind>("character");
  const [form, setForm] = useState({ conduct: "Good", purpose: "", leaving_date: isoDay(new Date()), reason: "", remarks: "", mark_left: true });
  const [recent, setRecent] = useState<Certificate[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("student");
    if (id) api<StudentHit>(`/api/students/${id}/`).then(setStudent).catch(setError);
    apiList<Certificate>("/api/certificates/").then(setRecent).catch(setError);
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    const timer = setTimeout(() => {
      apiList<StudentHit>(`/api/students/?search=${encodeURIComponent(query.trim())}`).then((r) => setHits(r.slice(0, 8))).catch(() => setHits([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  async function issue(e: React.FormEvent) {
    e.preventDefault();
    if (!student) return;
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { student: student.id, kind, remarks: form.remarks, conduct: form.conduct };
      if (kind === "bonafide") body.purpose = form.purpose;
      if (kind === "leaving") Object.assign(body, { leaving_date: form.leaving_date, reason: form.reason, mark_left: form.mark_left });
      const cert = await api<Certificate>("/api/certificates/", { method: "POST", body: JSON.stringify(body) });
      router.push(`/certificates/view/?id=${cert.id}`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  const set = (key: keyof typeof form, value: string | boolean) => setForm({ ...form, [key]: value });

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold">Certificates</h1>
      <Card>
        <form onSubmit={issue} className="space-y-4">
          {student ? (
            <div className="flex items-center justify-between gap-3 rounded-xl bg-slate-100 px-3 py-2 dark:bg-slate-800">
              <div>
                <p className="font-medium">{student.full_name}</p>
                <p className="text-xs text-slate-500">
                  Adm {student.admission_no}
                  {student.current_enrollment && ` · ${student.current_enrollment.program_name} - ${student.current_enrollment.section_name}`}
                  {student.status !== "active" && ` · ${student.status}`}
                </p>
              </div>
              <button type="button" onClick={() => setStudent(null)} className="text-sm text-indigo-600 hover:underline">
                Change
              </button>
            </div>
          ) : (
            <div>
              <Field label="Student" placeholder="Type a name or admission number" value={query} onChange={(e) => setQuery(e.target.value)} autoComplete="off" />
              {hits.length > 0 && (
                <ul className="mt-1 divide-y divide-slate-200 rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-700">
                  {hits.map((h) => (
                    <li key={h.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setStudent(h);
                          setQuery("");
                          setHits([]);
                        }}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      >
                        <span className="font-medium">{h.full_name}</span>{" "}
                        <span className="text-xs text-slate-500">
                          Adm {h.admission_no}
                          {h.current_enrollment && ` · ${h.current_enrollment.program_name} - ${h.current_enrollment.section_name}`}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <fieldset className="grid gap-2 sm:grid-cols-3">
            <legend className="mb-1 text-sm font-medium">Certificate</legend>
            {KINDS.map((k) => (
              <label key={k.value} className={`cursor-pointer rounded-xl border p-3 text-sm ${kind === k.value ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950" : "border-slate-300 dark:border-slate-700"}`}>
                <input type="radio" name="kind" className="sr-only" checked={kind === k.value} onChange={() => setKind(k.value)} />
                <span className="block font-medium">{k.title}</span>
                <span className="text-xs text-slate-500">{k.about}</span>
              </label>
            ))}
          </fieldset>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Conduct / character" value={form.conduct} onChange={(e) => set("conduct", e.target.value)} placeholder="Good, Very good, Excellent" />
            {kind === "bonafide" && <Field label="Purpose (optional)" placeholder="e.g. passport application" value={form.purpose} onChange={(e) => set("purpose", e.target.value)} />}
            {kind === "leaving" && (
              <>
                <Field label="Date of leaving" type="date" value={form.leaving_date} onChange={(e) => set("leaving_date", e.target.value)} required />
                <Field label="Reason for leaving" placeholder="e.g. family moved to another city" value={form.reason} onChange={(e) => set("reason", e.target.value)} required />
                <label className="flex items-center gap-2 self-end pb-2 text-sm">
                  <input type="checkbox" checked={form.mark_left} onChange={(e) => set("mark_left", e.target.checked)} />
                  Mark the student as left
                </label>
              </>
            )}
          </div>
          <Field label="Remarks (optional)" value={form.remarks} onChange={(e) => set("remarks", e.target.value)} />
          <ErrorBox error={error} />
          <Button type="submit" disabled={!student || busy}>
            {busy ? "Issuing…" : "Issue certificate"}
          </Button>
        </form>
      </Card>

      <Card>
        <h2 className="mb-2 font-medium">Issued certificates</h2>
        {recent.length === 0 ? (
          <p className="text-sm text-slate-500">None yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-800">
            {recent.map((c) => (
              <li key={c.id}>
                <Link href={`/certificates/view/?id=${c.id}`} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <span>
                    <span className="font-medium">{c.data.full_name}</span> <span className="text-slate-500">· {c.kind_label}</span>
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">
                    {certificateNo(c.number)} · {longDate(c.issued_on)} ›
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
