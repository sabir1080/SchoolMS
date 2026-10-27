"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import type { AcademicSession, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { APPLICATION_TABS, applicationNo, applyLink, type Application, type ApplicationStatus } from "@/lib/admissions";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/navigation";
import { GENDERS, RELATIONS, label } from "@/lib/students";
import { termsFor } from "@/lib/terms";
import { useLatestRequest } from "@/lib/useLatestRequest";

export default function AdmissionsPage() {
  const { user } = useAuth();
  const [open, setOpen] = useState<boolean | null>(null);
  const [tab, setTab] = useState<ApplicationStatus>("new");
  const [apps, setApps] = useState<Application[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [copied, setCopied] = useState(false);
  const latest = useLatestRequest();
  const code = user?.tenant?.slug ?? "";

  useEffect(() => {
    api<{ admissions_open: boolean }>("/api/institute/settings/")
      .then((s) => setOpen(s.admissions_open))
      .catch(setError);
  }, []);

  const load = useCallback(() => {
    setApps(null);
    latest(api<Application[]>(`/api/admissions/?status=${tab}`), setApps, setError);
  }, [tab, latest]);

  useEffect(load, [load]);

  async function toggle() {
    setError(null);
    try {
      const s = await api<{ admissions_open: boolean }>("/api/institute/settings/", {
        method: "PATCH",
        body: JSON.stringify({ admissions_open: !open }),
      });
      setOpen(s.admissions_open);
    } catch (err) {
      setError(err);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(applyLink(code));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  const link = applyLink(code);
  const share = `https://wa.me/?text=${encodeURIComponent(`${user?.tenant?.name}: Apply for admission online: ${link}`)}`;

  return (
    <div className="max-w-4xl space-y-4">
      <h1 className="text-2xl font-semibold">Admissions</h1>
      <ErrorBox error={error} />

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-medium">Online admission form</h2>
            <p className="text-sm text-slate-500">
              {open ? "Open: parents can apply from the link below." : "Closed: parents cannot send applications."}
            </p>
          </div>
          {open !== null && (
            <Button type="button" onClick={toggle} className={open ? "bg-slate-600 hover:bg-slate-700" : ""}>
              {open ? "Close the form" : "Open the form"}
            </Button>
          )}
        </div>
        {open && (
          <div className="mt-3 space-y-2">
            <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm break-all dark:bg-slate-800" data-testid="apply-link">
              {link}
            </p>
            <div className="flex flex-wrap gap-2 text-sm">
              <button onClick={copy} className="rounded-lg border border-slate-300 px-3 py-1.5 dark:border-slate-700">
                {copied ? "Copied" : "Copy link"}
              </button>
              <a href={share} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-300 px-3 py-1.5 dark:border-slate-700">
                Share on WhatsApp
              </a>
              <a href={link} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-300 px-3 py-1.5 dark:border-slate-700">
                Open the form
              </a>
            </div>
            <p className="text-xs text-slate-500">Parents also see “Apply for admission” on your login page after entering your institute code.</p>
          </div>
        )}
      </Card>

      <div className="flex gap-2">
        {APPLICATION_TABS.map(([value, text]) => (
          <button
            key={value}
            onClick={() => {
              setTab(value);
              setSelected(null);
            }}
            className={`rounded-full px-3 py-1 text-sm ${tab === value ? "bg-brand-600 text-white" : "bg-white dark:bg-slate-900"}`}
          >
            {text}
          </button>
        ))}
      </div>

      {apps === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : apps.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">No applications here.</p>
        </Card>
      ) : (
        <ul className="space-y-2">
          {apps.map((app) => (
            <li key={app.id}>
              <Card>
                <button onClick={() => setSelected(selected === app.id ? null : app.id)} className="flex w-full items-start justify-between gap-3 text-left">
                  <span className="min-w-0">
                    <span className="block font-medium">{app.full_name}</span>
                    <span className="block text-xs text-slate-500">
                      {applicationNo(app.number)} · {app.program_name ?? "Class not chosen"} · {app.guardian_name} ({app.guardian_phone})
                    </span>
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">{formatDate(app.created_at)}</span>
                </button>
                {selected === app.id && <ApplicationDetail app={app} onDone={load} />}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ApplicationDetail({ app, onDone }: { app: Application; onDone: () => void }) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const current = sessions.items.find((s) => s.is_current);
  const sections = useList<Section>(current ? `/api/academics/sections/?session=${current.id}` : null);
  const [section, setSection] = useState("");
  const [roll, setRoll] = useState("");
  const [admissionNo, setAdmissionNo] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  // Suggest the first section of the class the parent applied for.
  useEffect(() => {
    if (section || !sections.items.length) return;
    const match = sections.items.find((s) => s.program === app.program);
    if (match) setSection(String(match.id));
  }, [sections.items, app.program, section]);

  async function decide(action: "approve" | "reject") {
    if (action === "reject" && !confirm(`Decline ${app.full_name}'s application?`)) return;
    setBusy(true);
    setError(null);
    try {
      const body =
        action === "approve" ? { section: section ? Number(section) : null, roll_number: roll, admission_no: admissionNo } : { admin_note: note };
      await api(`/api/admissions/${app.id}/${action}/`, { method: "POST", body: JSON.stringify(body) });
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const rows: [string, string][] = [
    ["Gender", label(GENDERS, app.gender)],
    ["Date of birth", app.date_of_birth ? formatDate(app.date_of_birth) : "—"],
    [`${terms.program} applying for`, app.program_name ?? "Not sure"],
    ["Previous school", app.previous_school || "—"],
    [label(RELATIONS, app.guardian_relation), app.guardian_name],
    ["Mobile", app.guardian_phone],
    ["Email", app.guardian_email || "—"],
    ["CNIC / ID", app.guardian_cnic || "—"],
    ["Address", app.address || "—"],
  ];

  return (
    <div className="mt-4 space-y-4 border-t border-slate-200 pt-4 dark:border-slate-800">
      <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-slate-500">{k}</dt>
            <dd className="mb-1 sm:mb-0">{v}</dd>
          </div>
        ))}
      </dl>
      {app.message && <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800">“{app.message}”</p>}

      {app.status === "new" ? (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <SelectField
              label={`${terms.program} - ${terms.section}`}
              options={[["", `No ${terms.section.toLowerCase()} yet`], ...sections.items.map((s): [string, string] => [String(s.id), `${s.program_name} - ${s.name}`])]}
              value={section}
              onChange={(e) => setSection(e.target.value)}
            />
            <Field label="Roll number (optional)" value={roll} onChange={(e) => setRoll(e.target.value)} maxLength={20} />
            <Field label="Admission No. (empty = automatic)" value={admissionNo} onChange={(e) => setAdmissionNo(e.target.value)} maxLength={30} />
          </div>
          <ErrorBox error={error} />
          <div className="flex flex-wrap items-end gap-3">
            <Button type="button" onClick={() => decide("approve")} disabled={busy}>
              Admit student
            </Button>
            <div className="flex flex-1 flex-wrap items-end gap-2">
              <div className="min-w-48 flex-1">
                <Field label="Reason (optional)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={255} />
              </div>
              <button type="button" onClick={() => decide("reject")} disabled={busy} className="rounded-lg border border-red-300 px-3 py-2 text-sm text-red-600">
                Decline
              </button>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {app.status_label}
          {app.decided_at && ` on ${formatDate(app.decided_at)}`}
          {app.decided_by_name && ` by ${app.decided_by_name}`}
          {app.admin_note && ` · ${app.admin_note}`}
          {app.student && (
            <>
              {" · "}
              <Link href={`/students/view/?id=${app.student}`} className="text-brand-600 hover:underline">
                Open student
              </Link>
            </>
          )}
        </p>
      )}
    </div>
  );
}
