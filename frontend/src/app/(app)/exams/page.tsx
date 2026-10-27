"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { AcademicSession, Program } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { ExamForm } from "@/components/exams/ExamForm";
import { ExamStatusBadge, ExamsTabs } from "@/components/exams/ExamsTabs";
import { Card, ErrorBox, SelectField } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { EXAM_STATUS, EXAM_TYPES, shortDate, type Exam } from "@/lib/exams";
import { label } from "@/lib/students";

export default function ExamsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const isAdmin = user?.role === "admin";
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const programs = useList<Program>("/api/academics/programs/");
  const [sessionId, setSessionId] = useState("");
  const exams = useList<Exam>(sessionId ? `/api/exams/?session=${sessionId}` : null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!sessionId && sessions.items.length) {
      setSessionId(String((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id));
    }
  }, [sessions.items, sessionId]);

  const session = sessions.items.find((s) => String(s.id) === sessionId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Exams</h1>
        {isAdmin && session && (
          <button onClick={() => setAdding(!adding)} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
            {adding ? "Close" : "+ New exam"}
          </button>
        )}
      </div>
      <ExamsTabs />
      <ErrorBox error={exams.error} />

      {sessions.loaded && sessions.items.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">Add an academic session first (Academic setup).</p>
        </Card>
      ) : (
        <div className="max-w-xs">
          <SelectField
            label="Session"
            options={sessions.items.map((s) => [String(s.id), s.is_current ? `${s.name} (current)` : s.name])}
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
        </div>
      )}

      {adding && session && (
        <Card>
          <h2 className="mb-3 font-medium">New exam in {session.name}</h2>
          <ExamForm
            session={session}
            programs={programs.items}
            onSaved={(exam) => router.push(`/exams/exam/?id=${exam.id}`)}
          />
        </Card>
      )}

      {exams.loaded && exams.items.length === 0 && (
        <Card>
          <p className="text-sm text-slate-500">
            No exams in this session yet.{isAdmin && " Use “New exam” to add First Term, Mid-term, Final or a monthly test."}
          </p>
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {exams.items.map((exam) => (
          <Link key={exam.id} href={`/exams/exam/?id=${exam.id}`} className="block rounded-2xl bg-white p-4 shadow-sm hover:ring-1 hover:ring-indigo-200 dark:bg-slate-900">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate font-semibold">{exam.name}</p>
                <p className="text-xs text-slate-500">
                  {label(EXAM_TYPES, exam.exam_type)}
                  {exam.start_date && ` · ${shortDate(exam.start_date, true)}`}
                  {exam.end_date && ` – ${shortDate(exam.end_date, true)}`}
                </p>
              </div>
              <ExamStatusBadge {...EXAM_STATUS[exam.status]} />
            </div>
            <p className="mt-2 truncate text-sm text-slate-600 dark:text-slate-300">{exam.program_names.join(", ")}</p>
            <p className="text-xs text-slate-500">{exam.paper_count} papers</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
