"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { percentText, sectionText, STATUS_OPTIONS, type SectionInfo, type Summary } from "@/lib/attendance";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";

interface Today {
  sections: number;
  marked_sections: number;
  unmarked: SectionInfo[];
  summary: Summary;
}

/** Dashboard card for admins and teachers: today's attendance at a glance. */
export function TodayCard() {
  const { user, subscription } = useAuth();
  const [today, setToday] = useState<Today | null>(null);
  const terms = termsFor(user?.tenant);
  const enabled =
    (user?.role === "admin" || user?.role === "teacher") &&
    subscription?.is_usable &&
    subscription.plan.features.includes("attendance");

  useEffect(() => {
    if (enabled) api<Today>("/api/attendance/today/").then(setToday).catch(() => setToday(null));
  }, [enabled]);

  if (!enabled || !today || today.sections === 0) return null;

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm md:p-6 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-medium">Today&apos;s attendance</h2>
        <Link href="/attendance/" className="text-sm text-indigo-600 hover:underline">
          Take attendance
        </Link>
      </div>
      <p className="mt-1 text-3xl font-semibold">{percentText(today.summary)}</p>
      <div className="mt-2 flex flex-wrap gap-3 text-sm">
        {STATUS_OPTIONS.map((o) => (
          <span key={o.value} className="flex items-center gap-1">
            <span className={`h-2.5 w-2.5 rounded-full ${o.dot}`} />
            {o.label} {today.summary[o.value]}
          </span>
        ))}
      </div>
      <p className="mt-3 text-sm text-slate-500">
        {today.marked_sections} of {today.sections} {terms.sections.toLowerCase()} marked.
        {today.unmarked.length > 0 && <> Not yet: {today.unmarked.map((s) => sectionText(s, terms.section)).join(", ")}.</>}
      </p>
    </div>
  );
}
