"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { AcademicSession } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { CombinedForm } from "@/components/exams/CombinedForm";
import { ExamStatusBadge, ExamsTabs } from "@/components/exams/ExamsTabs";
import { Card, ErrorBox, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { COMBINED_STATUS, type Combined, type Exam } from "@/lib/exams";

export default function CombinedPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const [sessionId, setSessionId] = useState("");
  const results = useList<Combined>(sessionId ? `/api/combined-results/?session=${sessionId}` : null);
  const exams = useList<Exam>(sessionId ? `/api/exams/?session=${sessionId}` : null);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!sessionId && sessions.items.length) {
      setSessionId(String((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id));
    }
  }, [sessions.items, sessionId]);

  const session = sessions.items.find((s) => String(s.id) === sessionId);
  const sortedExams = [...exams.items].sort((a, b) => (a.start_date ?? "9").localeCompare(b.start_date ?? "9"));

  async function act(c: Combined, method: "PATCH" | "DELETE", body?: object) {
    if (method === "DELETE" && !window.confirm(`Delete "${c.name}"? Marks stay in the exams.`)) return;
    setError(null);
    try {
      await api(`/api/combined-results/${c.id}/`, { method, body: body ? JSON.stringify(body) : undefined });
      results.reload();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Exams</h1>
        {isAdmin && session && (
          <button onClick={() => setEditing(editing === "new" ? null : "new")} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white">
            {editing === "new" ? "Close" : "+ Annual result"}
          </button>
        )}
      </div>
      <ExamsTabs />
      <p className="max-w-2xl text-sm text-slate-500">
        The annual (combined) result adds up several exams with your school&apos;s weightage, for example First Term 25%, Mid-Term 25% and
        Final 50%. Parents and students see it once you publish it.
      </p>
      <div className="max-w-xs">
        <SelectField
          label="Session"
          options={sessions.items.map((s) => [String(s.id), s.is_current ? `${s.name} (current)` : s.name])}
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
        />
      </div>
      <ErrorBox error={error ?? results.error} />

      {editing === "new" && session && (
        <Card>
          <h2 className="mb-3 font-medium">New annual result</h2>
          <CombinedForm
            session={session}
            exams={sortedExams}
            onSaved={() => {
              setEditing(null);
              results.reload();
            }}
          />
        </Card>
      )}

      {results.loaded && results.items.length === 0 && editing !== "new" && (
        <Card>
          <p className="text-sm text-slate-500">No annual result in this session yet.{isAdmin && " Use “Annual result” to make one."}</p>
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {results.items.map((c) => (
          <Card key={c.id}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate font-semibold">{c.name}</p>
                <p className="text-xs text-slate-500">Session {c.session_name}</p>
              </div>
              <ExamStatusBadge {...COMBINED_STATUS[c.status]} />
            </div>
            <ul className="mt-3 space-y-1 text-sm">
              {c.components.map((comp) => (
                <li key={comp.exam} className="flex items-center justify-between gap-2">
                  <span>
                    {comp.exam_name}
                    {comp.exam_status !== "published" && <span className="ml-1 text-xs text-amber-700 dark:text-amber-300">(not published)</span>}
                  </span>
                  <span className="font-medium">{comp.weight}%</span>
                </li>
              ))}
            </ul>
            {editing === c.id && session ? (
              <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-800">
                <CombinedForm
                  session={session}
                  exams={sortedExams}
                  combined={c}
                  onSaved={() => {
                    setEditing(null);
                    results.reload();
                  }}
                />
              </div>
            ) : (
              <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
                <Link href={`/exams/combined/result/?id=${c.id}`} className="font-medium text-brand-600 hover:underline">
                  Result →
                </Link>
                {isAdmin && (
                  <>
                    {c.status === "draft" ? (
                      <button onClick={() => act(c, "PATCH", { status: "published" })} className="rounded-lg bg-brand-600 px-3 py-1.5 font-medium text-white">
                        Publish
                      </button>
                    ) : (
                      <button onClick={() => act(c, "PATCH", { status: "draft" })} className="text-slate-600 hover:underline dark:text-slate-300">
                        Unpublish
                      </button>
                    )}
                    <button onClick={() => setEditing(c.id)} className="text-brand-600 hover:underline">
                      Edit
                    </button>
                    <button onClick={() => act(c, "DELETE")} className="text-red-600 hover:underline">
                      Delete
                    </button>
                  </>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
