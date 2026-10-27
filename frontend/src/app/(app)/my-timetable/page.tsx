"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { TimetableGrid } from "@/components/timetable/TimetableGrid";
import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import type { Timetable } from "@/lib/timetable";

/** The week timetable of a parent's child (?student=) or the logged-in student. */
export default function MyTimetablePage() {
  const [data, setData] = useState<Timetable | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const student = new URLSearchParams(window.location.search).get("student");
    api<Timetable>(`/api/me/timetable/${student ? `?student=${student}` : ""}`).then(setData).catch(setError);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <Link href="/dashboard/" className="text-sm text-brand-600 hover:underline">
          ← Dashboard
        </Link>
        <button onClick={() => window.print()} className="text-sm text-brand-600 hover:underline">
          Print
        </button>
      </div>
      <ErrorBox error={error} />
      {data && (
        <Card>
          <h1 className="mb-3 text-lg font-semibold">
            Timetable{data.section && ` · ${data.section.program_name} - ${data.section.name}`}
          </h1>
          <TimetableGrid data={data} show="teacher" />
        </Card>
      )}
    </div>
  );
}
