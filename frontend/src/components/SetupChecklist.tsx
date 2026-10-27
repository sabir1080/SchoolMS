"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";

interface Counts {
  sessions: number;
  programs: number;
  sections: number;
  subjects: number;
  students: number;
}

/** Guides a new institute admin through the academic setup until it is done. */
export function SetupChecklist() {
  const { user, subscription } = useAuth();
  const [counts, setCounts] = useState<Counts | null>(null);

  const allowed = user?.role === "admin" && subscription?.is_usable && subscription.plan.features.includes("academics");

  useEffect(() => {
    if (!allowed) return;
    const count = (path: string) => api<{ count: number }>(`${path}?page_size=1`).then((d) => d.count);
    Promise.all([
      count("/api/academics/sessions/"),
      count("/api/academics/programs/"),
      count("/api/academics/sections/"),
      count("/api/academics/subjects/"),
      count("/api/students/"),
    ])
      .then(([sessions, programs, sections, subjects, students]) =>
        setCounts({ sessions, programs, sections, subjects, students }),
      )
      .catch(() => setCounts(null));
  }, [allowed]);

  if (!allowed || !counts) return null;
  type Step = { done: boolean; label: string; tab?: string; href?: string };
  const terms = termsFor(user?.tenant);
  const steps = [
    { done: counts.sessions > 0, label: "Add the academic session (e.g. 2026-27)", tab: "sessions" } as Step,
    { done: counts.programs > 0, label: `Add your ${terms.programs.toLowerCase()}`, tab: "programs" },
    { done: counts.subjects > 0, label: "Add subjects", tab: "subjects" },
    { done: counts.sections > 0, label: `Add ${terms.sections.toLowerCase()} and class teachers`, tab: "sections" },
    { done: counts.students > 0, label: "Admit your first student", href: "/students/new" },
  ];
  if (steps.every((s) => s.done)) return null;

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm md:p-6 dark:bg-slate-900">
      <h2 className="font-medium">Get started</h2>
      <p className="mb-3 text-sm text-slate-500">Set up your institute in a few steps.</p>
      <ol className="space-y-2">
        {steps.map((step, i) => (
          <li key={step.label} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                step.done ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200"
              }`}
            >
              {step.done ? "✓" : i + 1}
            </span>
            {step.done ? (
              <span className="text-slate-500 line-through">{step.label}</span>
            ) : (
              <Link href={step.href ?? `/academics/?tab=${step.tab}`} className="text-brand-600 hover:underline">
                {step.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
