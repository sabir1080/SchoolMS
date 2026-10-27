"use client";

import { useEffect, useMemo, useState } from "react";

import type { AcademicSession, Program } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { FeesTabs } from "@/components/fees/FeesTabs";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { COMMON_FEES, FREQUENCIES, money, type FeeHead } from "@/lib/fees";
import { termsFor } from "@/lib/terms";

interface Rate {
  program: number;
  fee_head: number;
  amount: string;
}

export default function FeeSetupPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const heads = useList<FeeHead>("/api/fees/heads/");
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const programs = useList<Program>("/api/academics/programs/");
  const [sessionId, setSessionId] = useState("");
  const [rates, setRates] = useState<Rate[]>([]);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!sessionId && sessions.items.length) {
      setSessionId(String((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id));
    }
  }, [sessions.items, sessionId]);

  useEffect(() => {
    if (sessionId) api<Rate[]>(`/api/fees/rates/?session=${sessionId}`).then(setRates).catch(setError);
  }, [sessionId]);

  const activeHeads = heads.items.filter((h) => h.is_active);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Fees</h1>
      <FeesTabs />
      <ErrorBox error={error || heads.error} />

      <Card>
        <h2 className="mb-1 font-medium">1. Fee types</h2>
        <p className="mb-3 text-sm text-slate-500">
          Monthly fees are added to every monthly bill. &quot;Once per session&quot; fees (like admission) are added
          only to a student&apos;s first bill of the session.
        </p>
        <FeeHeads heads={heads.items} onChanged={heads.reload} />
      </Card>

      <Card>
        <h2 className="mb-1 font-medium">2. Fees for each {terms.program.toLowerCase()}</h2>
        {sessions.loaded && sessions.items.length === 0 ? (
          <p className="text-sm text-slate-500">Add an academic session first (Academic setup).</p>
        ) : activeHeads.length === 0 ? (
          <p className="text-sm text-slate-500">Add fee types above first.</p>
        ) : (
          <>
            <div className="mb-4 max-w-xs">
              <SelectField
                label="Session"
                options={sessions.items.map((s) => [String(s.id), s.is_current ? `${s.name} (current)` : s.name])}
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
              />
            </div>
            <div className="space-y-3">
              {programs.items
                .filter((p) => p.is_active)
                .map((p) => (
                  <ProgramRates
                    key={`${sessionId}-${p.id}`}
                    program={p}
                    sessionId={Number(sessionId)}
                    heads={activeHeads}
                    rates={rates.filter((r) => r.program === p.id)}
                    allRates={rates}
                    programs={programs.items}
                    onSaved={setRates}
                  />
                ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

function FeeHeads({ heads, onChanged }: { heads: FeeHead[]; onChanged: () => void }) {
  const [name, setName] = useState("");
  const [frequency, setFrequency] = useState("monthly");
  const [error, setError] = useState<unknown>(null);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/fees/heads/", { method: "POST", body: JSON.stringify({ name, frequency, sort_order: heads.length }) });
      setName("");
      onChanged();
    } catch (err) {
      setError(err);
    }
  }

  async function addCommon() {
    setError(null);
    const existing = new Set(heads.map((h) => h.name.toLowerCase()));
    try {
      let order = heads.length;
      for (const fee of COMMON_FEES.filter((f) => !existing.has(f.name.toLowerCase()))) {
        await api("/api/fees/heads/", { method: "POST", body: JSON.stringify({ ...fee, sort_order: order++ }) });
      }
      onChanged();
    } catch (err) {
      setError(err);
    }
  }

  async function update(head: FeeHead, patch: Partial<FeeHead>) {
    try {
      await api(`/api/fees/heads/${head.id}/`, { method: "PATCH", body: JSON.stringify(patch) });
      onChanged();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="space-y-3">
      {heads.length > 0 && (
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {heads.map((h) => (
            <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
              <span className={h.is_active ? "font-medium" : "text-slate-400 line-through"}>{h.name}</span>
              <span className="flex items-center gap-3">
                <select
                  value={h.frequency}
                  onChange={(e) => update(h, { frequency: e.target.value as FeeHead["frequency"] })}
                  aria-label={`How often ${h.name} is charged`}
                  className="rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900"
                >
                  {FREQUENCIES.map(([v, t]) => (
                    <option key={v} value={v}>
                      {t}
                    </option>
                  ))}
                </select>
                <button onClick={() => update(h, { is_active: !h.is_active })} className="text-xs text-indigo-600 hover:underline">
                  {h.is_active ? "Turn off" : "Turn on"}
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end">
        <Field label="New fee type" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Computer Lab Fee" required />
        <SelectField label="Charged" options={FREQUENCIES} value={frequency} onChange={(e) => setFrequency(e.target.value)} />
        <Button type="submit">Add</Button>
      </form>
      {heads.length === 0 && (
        <button type="button" onClick={addCommon} className="rounded-lg border border-slate-300 px-4 py-2 text-sm dark:border-slate-700">
          Add common fees (Tuition, Admission, Annual, Exam, Transport)
        </button>
      )}
      <ErrorBox error={error} />
    </div>
  );
}

function ProgramRates({
  program,
  sessionId,
  heads,
  rates,
  allRates,
  programs,
  onSaved,
}: {
  program: Program;
  sessionId: number;
  heads: FeeHead[];
  rates: Rate[];
  allRates: Rate[];
  programs: Program[];
  onSaved: (rates: Rate[]) => void;
}) {
  const { user } = useAuth();
  const initial = useMemo(
    () => Object.fromEntries(heads.map((h) => [h.id, rates.find((r) => r.fee_head === h.id)?.amount.replace(/\.00$/, "") ?? ""])),
    [heads, rates],
  );
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<number, string>>(initial);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => setValues(initial), [initial]);

  const monthly = heads.filter((h) => h.frequency === "monthly").reduce((sum, h) => sum + Number(initial[h.id] || 0), 0);
  const sources = programs.filter((p) => p.id !== program.id && allRates.some((r) => r.program === p.id));

  function copyFrom(programId: string) {
    const from = allRates.filter((r) => r.program === Number(programId));
    setValues(Object.fromEntries(heads.map((h) => [h.id, from.find((r) => r.fee_head === h.id)?.amount.replace(/\.00$/, "") ?? ""])));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    try {
      const result = await api<Rate[]>("/api/fees/rates/", {
        method: "POST",
        body: JSON.stringify({
          session: sessionId,
          program: program.id,
          rates: heads.map((h) => ({ fee_head: h.id, amount: values[h.id] || "0" })),
        }),
      });
      onSaved(result);
      setSaved(true);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left"
        aria-expanded={open}
      >
        <span className="font-medium">{program.name}</span>
        <span className="text-sm text-slate-500">
          {rates.length ? `${money(monthly, user?.tenant?.currency)} / month` : "Not set"} {open ? "▲" : "▼"}
        </span>
      </button>
      {open && (
        <form onSubmit={save} className="space-y-3 border-t border-slate-200 p-3 dark:border-slate-700">
          <div className="grid gap-3 sm:grid-cols-2">
            {heads.map((h) => (
              <Field
                key={h.id}
                label={`${h.name}${h.frequency === "one_time" ? " (once)" : " (monthly)"}`}
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                value={values[h.id] ?? ""}
                onChange={(e) => setValues({ ...values, [h.id]: e.target.value })}
                placeholder="0"
              />
            ))}
          </div>
          {sources.length > 0 && (
            <label className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">Copy from</span>
              <select
                defaultValue=""
                onChange={(e) => e.target.value && copyFrom(e.target.value)}
                className="rounded-lg border border-slate-300 bg-transparent px-2 py-1 dark:border-slate-700 dark:bg-slate-900"
              >
                <option value="">—</option>
                {sources.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <ErrorBox error={error} />
          {saved && <p className="text-sm text-emerald-700">Saved.</p>}
          <Button type="submit">Save {program.name} fees</Button>
        </form>
      )}
    </div>
  );
}
