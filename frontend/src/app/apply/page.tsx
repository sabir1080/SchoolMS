"use client";

import { useEffect, useState } from "react";

import { BrandLogo } from "@/components/BrandLogo";
import { Button, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { applicationNo, type PublicForm } from "@/lib/admissions";
import { applyBrand } from "@/lib/brand";
import { GENDERS, RELATIONS } from "@/lib/students";
import { defaultTermsFor } from "@/lib/terms";

const EMPTY = {
  first_name: "",
  last_name: "",
  gender: "",
  date_of_birth: "",
  program: "",
  previous_school: "",
  guardian_name: "",
  guardian_relation: "father",
  guardian_phone: "",
  guardian_email: "",
  guardian_cnic: "",
  address: "",
  message: "",
  website: "",
};

const textarea =
  "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700";

/** The institute's online admission form, for parents (no login). */
export default function ApplyPage() {
  const [code, setCode] = useState("");
  const [info, setInfo] = useState<PublicForm | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<unknown>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<{
    number: number;
    full_name: string;
  } | null>(null);

  useEffect(() => {
    const value = (
      new URLSearchParams(window.location.search).get("code") ?? ""
    )
      .trim()
      .toLowerCase();
    setCode(value);
    if (!value) {
      setLoadError(
        new Error(
          "This link is missing the institute code. Please ask the school for the admission link.",
        ),
      );
      return;
    }
    api<PublicForm>(
      `/api/public/admissions/${encodeURIComponent(value)}/`,
      {},
      false,
    )
      .then((data) => {
        setInfo(data);
        applyBrand(data.brand?.hex);
      })
      .catch(setLoadError);
  }, []);

  const set =
    (key: keyof typeof EMPTY) =>
    (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >,
    ) =>
      setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = {
        ...form,
        program: form.program ? Number(form.program) : null,
        date_of_birth: form.date_of_birth || null,
      };
      setSent(
        await api(
          `/api/public/admissions/${encodeURIComponent(code)}/`,
          { method: "POST", body: JSON.stringify(body) },
          false,
        ),
      );
      setForm(EMPTY);
      window.scrollTo(0, 0);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const program = info ? defaultTermsFor(info.institute_type).program : "Class";

  return (
    <main className="flex min-h-screen justify-center px-4 py-8">
      <div className="w-full max-w-2xl space-y-4">
        {!info ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-slate-900">
            {loadError ? (
              <ErrorBox error={loadError} />
            ) : (
              <p className="text-sm text-slate-500">Loading…</p>
            )}
          </div>
        ) : (
          <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-slate-900">
            <div className="flex items-center gap-3">
              <BrandLogo src={info.brand?.logo} className="h-14 w-14" />
              <div className="min-w-0">
                <h1 className="text-2xl font-semibold">{info.name}</h1>
                <p className="text-sm text-slate-500">Online admission form</p>
              </div>
            </div>
            {(info.address || info.phone) && (
              <p className="mt-2 text-xs text-slate-500">
                {[info.address, info.phone].filter(Boolean).join(" · ")}
              </p>
            )}

            {sent ? (
              <div className="mt-6 space-y-3">
                <div className="rounded-xl bg-emerald-50 p-4 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                  <p className="font-semibold">Application received</p>
                  <p className="mt-1 text-sm">
                    Thank you. {sent.full_name}&apos;s application number is{" "}
                    <strong>{applicationNo(sent.number)}</strong>. The school
                    will contact you on your mobile number.
                  </p>
                </div>
                <button
                  onClick={() => setSent(null)}
                  className="text-sm text-brand-600 hover:underline"
                >
                  Apply for another child
                </button>
              </div>
            ) : !info.open ? (
              <p className="mt-6 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                Online admissions are closed right now. Please contact the
                school.
              </p>
            ) : (
              <form onSubmit={onSubmit} className="mt-6 space-y-6">
                <fieldset className="space-y-3">
                  <legend className="mb-2 font-medium">Student</legend>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field
                      label="First name"
                      value={form.first_name}
                      onChange={set("first_name")}
                      required
                      maxLength={100}
                    />
                    <Field
                      label="Last name"
                      value={form.last_name}
                      onChange={set("last_name")}
                      maxLength={100}
                    />
                    <SelectField
                      label="Gender"
                      options={[["", "Choose…"], ...GENDERS]}
                      value={form.gender}
                      onChange={set("gender")}
                      required
                    />
                    <Field
                      label="Date of birth"
                      type="date"
                      value={form.date_of_birth}
                      onChange={set("date_of_birth")}
                    />
                    <SelectField
                      label={`${program} applying for`}
                      options={[
                        ["", "Not sure"],
                        ...info.programs.map((p): [string, string] => [
                          String(p.id),
                          p.name,
                        ]),
                      ]}
                      value={form.program}
                      onChange={set("program")}
                    />
                    <Field
                      label="Previous school (if any)"
                      value={form.previous_school}
                      onChange={set("previous_school")}
                      maxLength={150}
                    />
                  </div>
                </fieldset>
                <fieldset className="space-y-3">
                  <legend className="mb-2 font-medium">
                    Parent / guardian
                  </legend>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field
                      label="Parent / guardian name"
                      value={form.guardian_name}
                      onChange={set("guardian_name")}
                      required
                      maxLength={150}
                    />
                    <SelectField
                      label="Relation"
                      options={RELATIONS}
                      value={form.guardian_relation}
                      onChange={set("guardian_relation")}
                    />
                    <Field
                      label="Mobile number"
                      type="tel"
                      inputMode="tel"
                      placeholder="0300-1234567"
                      value={form.guardian_phone}
                      onChange={set("guardian_phone")}
                      required
                      maxLength={30}
                    />
                    <Field
                      label="Email (optional)"
                      type="email"
                      value={form.guardian_email}
                      onChange={set("guardian_email")}
                    />
                    <Field
                      label="CNIC / ID number (optional)"
                      value={form.guardian_cnic}
                      onChange={set("guardian_cnic")}
                      maxLength={30}
                    />
                  </div>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium">Home address</span>
                    <textarea
                      value={form.address}
                      onChange={set("address")}
                      rows={2}
                      maxLength={500}
                      className={textarea}
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium">
                      Anything you want to tell the school (optional)
                    </span>
                    <textarea
                      value={form.message}
                      onChange={set("message")}
                      rows={3}
                      maxLength={1000}
                      className={textarea}
                    />
                  </label>
                </fieldset>
                {/* Left empty by people; bots that fill every field are refused. */}
                <input
                  type="text"
                  name="website"
                  value={form.website}
                  onChange={set("website")}
                  tabIndex={-1}
                  autoComplete="off"
                  aria-hidden="true"
                  className="absolute -left-[9999px] h-px w-px opacity-0"
                />
                <ErrorBox error={error} />
                <Button
                  type="submit"
                  disabled={busy}
                  className="w-full sm:w-auto"
                >
                  {busy ? "Sending…" : "Send application"}
                </Button>
              </form>
            )}
          </div>
        )}
        <p className="text-center text-xs text-slate-400">
          Powered by SchoolMS
        </p>
      </div>
    </main>
  );
}
