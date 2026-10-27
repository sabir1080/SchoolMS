"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CombinedCard } from "@/components/exams/CombinedCard";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CombinedResults } from "@/lib/exams";

export default function CombinedCardPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState<{ id: string; section: string; student: string } | null>(null);
  const [data, setData] = useState<CombinedResults | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const q = { id: p.get("id") ?? "", section: p.get("section") ?? "", student: p.get("student") ?? "" };
    setQuery(q);
    api<CombinedResults>(`/api/combined-results/${q.id}/results/?section=${q.section}&attendance=1`).then(setData).catch(setError);
  }, []);

  if (!data || !query) return <ErrorBox error={error} />;
  const index = data.students.findIndex((s) => String(s.student) === query.student);
  const row = data.students[index];
  if (!row) return <ErrorBox error={new Error("Student not found in this section.")} />;
  const link = (i: number) => `/exams/combined/card/?id=${query.id}&section=${query.section}&student=${data.students[i].student}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href={`/exams/combined/result/?id=${query.id}&section=${query.section}`} className="text-sm text-brand-600 hover:underline">
          ← {data.combined.name}
        </Link>
        <div className="flex items-center gap-3 text-sm">
          {index > 0 && (
            <a href={link(index - 1)} className="text-brand-600 hover:underline">
              ‹ Previous
            </a>
          )}
          {index < data.students.length - 1 && (
            <a href={link(index + 1)} className="text-brand-600 hover:underline">
              Next ›
            </a>
          )}
          <button onClick={() => window.print()} className="rounded-lg bg-brand-600 px-3 py-2 font-medium text-white">
            Print
          </button>
        </div>
      </div>
      <CombinedCard data={data} row={row} tenant={user?.tenant} />
    </div>
  );
}
