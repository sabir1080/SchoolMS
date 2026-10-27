"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Program } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { StatusBadge } from "@/components/students/StatusBadge";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { enrollmentText, STATUSES, type StudentListItem } from "@/lib/students";
import { termsFor } from "@/lib/terms";

interface Page {
  count: number;
  next: string | null;
  results: StudentListItem[];
}

export default function StudentsPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const programs = useList<Program>("/api/academics/programs/");
  const [search, setSearch] = useState("");
  const [program, setProgram] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page) });
    if (search.trim()) params.set("search", search.trim());
    if (program === "none") params.set("unassigned", "1");
    else if (program) params.set("program", program);
    if (status) params.set("status", status);
    // Wait until the user stops typing before searching.
    const timer = setTimeout(() => {
      api<Page>(`/api/students/?${params}`)
        .then((d) => {
          setData(d);
          setError(null);
        })
        .catch(setError);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, program, status, page]);

  const isAdmin = user?.role === "admin";
  const selectClass =
    "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Students</h1>
        {isAdmin && (
          <Link href="/students/new">
            <Button>+ New admission</Button>
          </Link>
        )}
      </div>

      <Card>
        <div className="grid gap-3 sm:grid-cols-3">
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search name, admission no, parent phone"
            aria-label="Search students"
            className={selectClass}
          />
          <select
            value={program}
            onChange={(e) => {
              setProgram(e.target.value);
              setPage(1);
            }}
            aria-label={`Filter by ${terms.program.toLowerCase()}`}
            className={selectClass}
          >
            <option value="">All {terms.programs.toLowerCase()}</option>
            {programs.items.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
            <option value="none">Not assigned to a {terms.program.toLowerCase()}</option>
          </select>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by status"
            className={selectClass}
          >
            <option value="">All statuses</option>
            {STATUSES.map(([value, text]) => (
              <option key={value} value={value}>
                {text}
              </option>
            ))}
          </select>
        </div>
      </Card>

      <ErrorBox error={error} />
      {data && (
        <Card>
          <p className="mb-2 text-sm text-slate-500">
            {data.count} student{data.count === 1 ? "" : "s"}
          </p>
          {data.results.length === 0 ? (
            <p className="text-sm text-slate-500">
              No students found.{isAdmin && " Use “New admission” to add one."}
            </p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {data.results.map((s) => (
                <li key={s.id}>
                  <Link href={`/students/view/?id=${s.id}`} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {s.full_name} <span className="text-xs font-normal text-slate-500">#{s.admission_no}</span>
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {enrollmentText(s.current_enrollment, terms.section)}
                        {s.guardian_name && ` · ${s.guardian_name}`}
                        {s.guardian_phone && ` · ${s.guardian_phone}`}
                      </p>
                    </div>
                    <StatusBadge status={s.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {(data.next || page > 1) && (
            <div className="mt-3 flex justify-between text-sm">
              <button disabled={page === 1} onClick={() => setPage(page - 1)} className="text-indigo-600 disabled:opacity-30">
                ← Previous
              </button>
              <button disabled={!data.next} onClick={() => setPage(page + 1)} className="text-indigo-600 disabled:opacity-30">
                Next →
              </button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
