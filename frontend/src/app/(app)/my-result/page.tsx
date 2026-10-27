"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CombinedCard } from "@/components/exams/CombinedCard";
import { ReportCard } from "@/components/exams/ReportCard";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { MyResults } from "@/lib/exams";

/** A parent's or student's own report card (exam or annual), ready to print or save as PDF. */
export default function MyResultPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState<{ kind: string; id: string } | null>(null);
  const [data, setData] = useState<MyResults | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    setQuery({ kind: p.get("kind") ?? "exam", id: p.get("id") ?? "" });
    const student = p.get("student");
    api<MyResults>(`/api/me/results/${student ? `?student=${student}` : ""}`).then(setData).catch(setError);
  }, []);

  if (!data || !query) return <ErrorBox error={error} />;
  const exam = query.kind === "exam" ? data.exams.find((e) => String(e.exam.id) === query.id) : undefined;
  const combined = query.kind === "combined" ? data.combined.find((c) => String(c.combined.id) === query.id) : undefined;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 print:hidden">
        <Link href="/dashboard/" className="text-sm text-indigo-600 hover:underline">
          ← Dashboard
        </Link>
        {(exam || combined) && (
          <button onClick={() => window.print()} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white">
            Print / Save PDF
          </button>
        )}
      </div>
      {exam && exam.students[0] && <ReportCard data={exam} row={exam.students[0]} tenant={user?.tenant} />}
      {combined && combined.students[0] && <CombinedCard data={combined} row={combined.students[0]} tenant={user?.tenant} />}
      {!exam && !combined && <ErrorBox error={new Error("This result is not available.")} />}
    </div>
  );
}
