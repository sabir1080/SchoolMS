"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, apiList } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BLOOD_GROUPS, GENDERS, RELATIONS, STATUSES, today, type GuardianInfo, type StudentDetail } from "@/lib/students";
import { termsFor } from "@/lib/terms";

import { SectionPicker, type SectionChoice } from "./SectionPicker";

interface GuardianRow {
  id?: number;
  name: string;
  phone: string;
  cnic: string;
  occupation: string;
  relation: string;
  is_primary: boolean;
  /** Children already linked to this guardian, shown when an existing guardian is found. */
  siblings?: string[];
}

const EMPTY_GUARDIAN: GuardianRow = { name: "", phone: "", cnic: "", occupation: "", relation: "father", is_primary: false };

function initialForm(student?: StudentDetail) {
  return {
    admission_no: student?.admission_no ?? "",
    first_name: student?.first_name ?? "",
    last_name: student?.last_name ?? "",
    gender: student?.gender ?? "male",
    date_of_birth: student?.date_of_birth ?? "",
    id_number: student?.id_number ?? "",
    blood_group: student?.blood_group ?? "",
    phone: student?.phone ?? "",
    email: student?.email ?? "",
    address: student?.address ?? "",
    admission_date: student?.admission_date ?? today(),
    previous_school: student?.previous_school ?? "",
    status: student?.status ?? "active",
    notes: student?.notes ?? "",
  };
}

function initialGuardians(student?: StudentDetail): GuardianRow[] {
  if (!student) return [{ ...EMPTY_GUARDIAN, is_primary: true }];
  return student.guardian_links.map((l) => ({
    id: l.guardian.id,
    name: l.guardian.name,
    phone: l.guardian.phone,
    cnic: l.guardian.cnic,
    occupation: l.guardian.occupation,
    relation: l.relation,
    is_primary: l.is_primary,
  }));
}

/** Admission form; with ``student`` it edits that student instead. */
export function StudentForm({ student }: { student?: StudentDetail }) {
  const { user } = useAuth();
  const router = useRouter();
  const terms = termsFor(user?.tenant);
  const [form, setForm] = useState(() => initialForm(student));
  const [guardians, setGuardians] = useState<GuardianRow[]>(() => initialGuardians(student));
  const [placement, setPlacement] = useState<SectionChoice>({ section: "", roll_number: "" });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof ReturnType<typeof initialForm>) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [key]: e.target.value });

  function setGuardian(index: number, patch: Partial<GuardianRow>) {
    setGuardians((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  /** When a phone number matches a guardian already in the institute, link to them (siblings). */
  async function lookupPhone(index: number) {
    const phone = guardians[index].phone.trim();
    if (!phone || guardians[index].id) return;
    try {
      const found = await apiList<GuardianInfo>(`/api/guardians/?phone=${encodeURIComponent(phone)}`);
      if (found.length) {
        const g = found[0];
        setGuardian(index, {
          id: g.id,
          name: g.name,
          cnic: g.cnic,
          occupation: g.occupation,
          siblings: g.children.map((c) => c.full_name),
        });
      }
    } catch {
      // Lookup is a convenience; the server links by phone anyway.
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      ...form,
      date_of_birth: form.date_of_birth || null,
      guardians: guardians
        .filter((g) => g.name.trim())
        .map((g) => ({
          id: g.id,
          name: g.name,
          phone: g.phone,
          cnic: g.cnic,
          occupation: g.occupation,
          relation: g.relation,
          is_primary: g.is_primary,
        })),
    };
    if (!student && placement.section) {
      body.enrollment = { section: Number(placement.section), roll_number: placement.roll_number };
    }
    try {
      const saved = await api<StudentDetail>(student ? `/api/students/${student.id}/` : "/api/students/", {
        method: student ? "PATCH" : "POST",
        body: JSON.stringify(body),
      });
      router.push(`/students/view/?id=${saved.id}${student ? "" : "&new=1"}`);
    } catch (err) {
      setError(err);
      setBusy(false);
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    }
  }

  return (
    <form onSubmit={onSubmit} className="max-w-3xl space-y-4">
      <Card>
        <h2 className="mb-4 font-medium">Student</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="First name" value={form.first_name} onChange={set("first_name")} required />
          <Field label="Last name" value={form.last_name} onChange={set("last_name")} />
          <SelectField label="Gender" options={GENDERS} value={form.gender} onChange={set("gender")} />
          <Field label="Date of birth" type="date" value={form.date_of_birth} onChange={set("date_of_birth")} />
          <Field label="B-Form / CNIC" value={form.id_number} onChange={set("id_number")} placeholder="e.g. 35202-1234567-1" />
          <SelectField
            label="Blood group"
            options={BLOOD_GROUPS.map((b): [string, string] => [b, b || "—"])}
            value={form.blood_group}
            onChange={set("blood_group")}
          />
          <Field label="Student phone (optional)" value={form.phone} onChange={set("phone")} />
          <Field label="Email (optional)" type="email" value={form.email} onChange={set("email")} />
          <label className="block space-y-1 sm:col-span-2">
            <span className="text-sm font-medium">Address</span>
            <textarea
              value={form.address}
              onChange={set("address")}
              rows={2}
              className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-slate-700"
            />
          </label>
        </div>
      </Card>

      <Card>
        <h2 className="mb-4 font-medium">Admission</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Field label="Admission number" value={form.admission_no} onChange={set("admission_no")} placeholder="Automatic" />
            {!student && <p className="mt-1 text-xs text-slate-500">Leave empty to number automatically.</p>}
          </div>
          <Field label="Admission date" type="date" value={form.admission_date} onChange={set("admission_date")} required />
          <Field label="Previous school (optional)" value={form.previous_school} onChange={set("previous_school")} />
          {student && <SelectField label="Status" options={STATUSES} value={form.status} onChange={set("status")} />}
        </div>
        {!student && (
          <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-800">
            <h3 className="mb-3 text-sm font-medium">
              {terms.program} &amp; {terms.section.toLowerCase()}
            </h3>
            <SectionPicker terms={terms} value={placement} onChange={setPlacement} />
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-1 font-medium">Parents / guardians</h2>
        <p className="mb-4 text-xs text-slate-500">
          Enter the phone number first: if this parent already has a child here, they are linked automatically.
        </p>
        <div className="space-y-4">
          {guardians.map((g, index) => (
            <div key={index} className="space-y-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Guardian {index + 1}</p>
                {guardians.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setGuardians(guardians.filter((_, i) => i !== index))}
                    className="text-sm text-red-600 hover:underline"
                  >
                    Remove
                  </button>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field
                  label="Phone"
                  type="tel"
                  value={g.phone}
                  onChange={(e) => setGuardian(index, { phone: e.target.value, id: undefined, siblings: undefined })}
                  onBlur={() => lookupPhone(index)}
                  placeholder="03xx-xxxxxxx"
                />
                <SelectField
                  label="Relation"
                  options={RELATIONS}
                  value={g.relation}
                  onChange={(e) => setGuardian(index, { relation: e.target.value })}
                />
                <Field label="Name" value={g.name} onChange={(e) => setGuardian(index, { name: e.target.value })} />
                <Field label="CNIC (optional)" value={g.cnic} onChange={(e) => setGuardian(index, { cnic: e.target.value })} />
                <Field
                  label="Occupation (optional)"
                  value={g.occupation}
                  onChange={(e) => setGuardian(index, { occupation: e.target.value })}
                />
              </div>
              {g.siblings && g.siblings.length > 0 && (
                <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                  Existing parent found: {g.name}. Already linked to {g.siblings.join(", ")}.
                </p>
              )}
              {guardians.length > 1 && (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="primary-guardian"
                    checked={g.is_primary}
                    onChange={() => setGuardians(guardians.map((row, i) => ({ ...row, is_primary: i === index })))}
                  />
                  Main contact
                </label>
              )}
            </div>
          ))}
        </div>
        {guardians.length < 4 && (
          <button
            type="button"
            onClick={() => setGuardians([...guardians, { ...EMPTY_GUARDIAN, relation: "mother" }])}
            className="mt-3 text-sm text-indigo-600 hover:underline"
          >
            + Add another guardian
          </button>
        )}
      </Card>

      <ErrorBox error={error} />
      <div className="flex gap-3">
        <Button type="submit" disabled={busy} className="py-2.5">
          {busy ? "Saving…" : student ? "Save changes" : "Admit student"}
        </Button>
        <button type="button" onClick={() => router.back()} className="text-sm text-slate-600 dark:text-slate-300">
          Cancel
        </button>
      </div>
    </form>
  );
}
