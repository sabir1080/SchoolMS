"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { AcademicSession, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { Button, Card, ErrorBox, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLatestRequest } from "@/lib/useLatestRequest";
import { termsFor } from "@/lib/terms";

type Action = "promote" | "repeat" | "left" | "graduated" | "skip";

interface Plan {
  section: { id: number; program_name: string; name: string; session_name: string };
  to_session: { id: number; name: string };
  next_program: { id: number; name: string } | null;
  promote_to: string | null;
  promote_to_new: boolean;
  repeat_in: string;
  result_source: string | null;
  students: {
    student: number;
    full_name: string;
    admission_no: string;
    roll_number: string;
    result: "pass" | "fail" | "incomplete" | null;
    percentage: string | null;
    suggested: Action;
    already: string | null;
  }[];
}

export default function PromotionPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const [fromSession, setFromSession] = useState("");
  const [toSession, setToSession] = useState("");
  const sections = useList<Section>(fromSession ? `/api/academics/sections/?session=${fromSession}` : null);
  const [sectionId, setSectionId] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [actions, setActions] = useState<Record<number, Action>>({});
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const latest = useLatestRequest();

  // Default: from the current session to the next one by start date.
  useEffect(() => {
    if (fromSession || !sessions.items.length) return;
    const ordered = [...sessions.items].sort((a, b) => a.start_date.localeCompare(b.start_date));
    const current = ordered.find((s) => s.is_current) ?? ordered[ordered.length - 1];
    setFromSession(String(current.id));
    const next = ordered.find((s) => s.start_date > current.start_date);
    if (next) setToSession(String(next.id));
  }, [sessions.items, fromSession]);

  const chosenSection = sectionId || (sections.items[0] ? String(sections.items[0].id) : "");

  useEffect(() => {
    setPlan(null);
    if (!chosenSection || !toSession) return;
    latest(
      api<Plan>(`/api/students/promotion/?section=${chosenSection}&to_session=${toSession}`),
      (p) => {
        setPlan(p);
        setActions(Object.fromEntries(p.students.map((s) => [s.student, s.suggested])));
      },
      setError,
    );
  }, [chosenSection, toSession, latest]);

  async function apply() {
    if (!plan) return;
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      const decisions = plan.students.filter((s) => actions[s.student] !== "skip").map((s) => ({ student: s.student, action: actions[s.student] }));
      const r = await api<Record<Action, number>>("/api/students/promotion/", {
        method: "POST",
        body: JSON.stringify({ section: plan.section.id, to_session: plan.to_session.id, decisions }),
      });
      setMessage(
        [r.promote && `${r.promote} promoted`, r.repeat && `${r.repeat} kept in the same class`, r.graduated && `${r.graduated} graduated`, r.left && `${r.left} marked as left`]
          .filter(Boolean)
          .join(", ") + ".",
      );
      const fresh = await api<Plan>(`/api/students/promotion/?section=${plan.section.id}&to_session=${plan.to_session.id}`);
      setPlan(fresh);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const others = sessions.items.filter((s) => String(s.id) !== fromSession);
  const label: Record<Action, string> = {
    promote: plan?.promote_to ? `Promote → ${plan.promote_to}` : "Promote",
    repeat: `Same class → ${plan?.repeat_in ?? ""}`,
    graduated: "Graduated (finished school)",
    left: "Left the school",
    skip: "Do nothing now",
  };
  const choices: Action[] = plan?.next_program ? ["promote", "repeat", "left", "skip"] : ["graduated", "repeat", "left", "skip"];
  const counts = plan ? choices.map((a) => [a, plan.students.filter((s) => actions[s.student] === a).length] as const) : [];

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <Link href="/students/" className="text-sm text-indigo-600 hover:underline">
          ← Students
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">Promote to next class</h1>
        <p className="text-sm text-slate-500">
          At the end of the year, move each {terms.section.toLowerCase()} into the new session. Suggestions come from the published result: passed →
          next {terms.program.toLowerCase()}, failed → same {terms.program.toLowerCase()}. Last year&apos;s records stay as they are.
        </p>
      </div>

      <Card>
        {sessions.loaded && sessions.items.length < 2 ? (
          <p className="text-sm text-slate-500">
            First add the new session (e.g. 2027-28) in{" "}
            <Link href="/academics/" className="text-indigo-600 hover:underline">
              Academic setup
            </Link>
            .
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-3">
            <SelectField
              label="From session"
              value={fromSession}
              onChange={(e) => {
                setFromSession(e.target.value);
                setSectionId("");
              }}
              options={sessions.items.map((s) => [String(s.id), s.name])}
            />
            <SelectField label={terms.section} value={chosenSection} onChange={(e) => setSectionId(e.target.value)} options={sections.items.map((s) => [String(s.id), `${s.program_name} - ${s.name}`])} />
            <SelectField label="To session" value={toSession} onChange={(e) => setToSession(e.target.value)} options={[["", "Choose…"], ...others.map((s) => [String(s.id), s.name] as [string, string])]} />
          </div>
        )}
      </Card>
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">{message}</p>}

      {plan && (
        <Card>
          <div className="mb-3 space-y-1 text-sm">
            <p>
              <span className="font-medium">
                {plan.section.program_name} - {plan.section.name}
              </span>{" "}
              ({plan.section.session_name}) → {plan.to_session.name}
            </p>
            <p className="text-slate-500">
              {plan.result_source ? `Suggestions from: ${plan.result_source}` : "No published result yet, so everyone is suggested for promotion."}
              {plan.promote_to_new && ` · ${plan.promote_to} will be created in ${plan.to_session.name}.`}
            </p>
          </div>
          {plan.students.length === 0 ? (
            <p className="text-sm text-slate-500">No active students in this section.</p>
          ) : (
            <>
              <div className="mb-3 flex flex-wrap gap-2 text-xs">
                {choices
                  .filter((a) => a !== "skip")
                  .map((a) => (
                    <button
                      key={a}
                      type="button"
                      onClick={() => setActions(Object.fromEntries(plan.students.map((s) => [s.student, a])))}
                      className="rounded-full border border-slate-300 px-3 py-1 dark:border-slate-700"
                    >
                      All: {a === "promote" ? "Promote" : a === "repeat" ? "Same class" : a === "graduated" ? "Graduated" : "Left"}
                    </button>
                  ))}
                <button
                  type="button"
                  onClick={() => setActions(Object.fromEntries(plan.students.map((s) => [s.student, s.suggested])))}
                  className="rounded-full border border-indigo-500 px-3 py-1 text-indigo-600"
                >
                  Use suggestions
                </button>
              </div>
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {plan.students.map((s) => (
                  <li key={s.student} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <div className="min-w-0">
                      <p className="font-medium">
                        {s.full_name} <span className="text-xs font-normal text-slate-500">Roll {s.roll_number || "—"}</span>
                      </p>
                      <p className="text-xs">
                        {s.result ? (
                          <span className={s.result === "fail" ? "text-red-600" : s.result === "pass" ? "text-emerald-700 dark:text-emerald-400" : "text-slate-500"}>
                            {s.result === "pass" ? "Passed" : s.result === "fail" ? "Failed" : "Incomplete"}
                            {s.percentage && ` · ${s.percentage}%`}
                          </span>
                        ) : (
                          <span className="text-slate-500">No result</span>
                        )}
                        {s.already && <span className="text-slate-500"> · already in {s.already}</span>}
                      </p>
                    </div>
                    <select
                      aria-label={`${s.full_name} decision`}
                      value={actions[s.student]}
                      onChange={(e) => setActions({ ...actions, [s.student]: e.target.value as Action })}
                      className="max-w-full rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                    >
                      {choices.map((a) => (
                        <option key={a} value={a}>
                          {label[a]}
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button onClick={apply} disabled={busy}>
                  {busy ? "Saving…" : "Apply"}
                </Button>
                <span className="text-xs text-slate-500">
                  {counts
                    .filter(([, n]) => n)
                    .map(([a, n]) => `${n} ${a === "promote" ? "promote" : a === "repeat" ? "same class" : a === "skip" ? "no change" : a}`)
                    .join(" · ")}
                </span>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
