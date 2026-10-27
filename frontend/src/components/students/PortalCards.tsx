"use client";

import { useEffect, useState } from "react";

import { StudentAttendanceCard } from "@/components/attendance/StudentAttendanceCard";
import { MyDateSheets } from "@/components/exams/MyDateSheets";
import { MyResultsCard } from "@/components/exams/MyResults";
import { MyFeesCard } from "@/components/fees/MyFeesCard";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/navigation";
import { enrollmentText, type Enrollment } from "@/lib/students";
import { termsFor } from "@/lib/terms";

interface Child {
  id: number;
  admission_no: string;
  full_name: string;
  date_of_birth: string | null;
  status: string;
  current_enrollment: Enrollment | null;
}

/** Dashboard cards for parents (their children) and students (their own profile). */
export function PortalCards() {
  const { user, subscription } = useAuth();
  const [children, setChildren] = useState<Child[] | null>(null);
  const terms = termsFor(user?.tenant);
  const role = user?.role;
  const enabled = (role === "parent" || role === "student") && subscription?.is_usable;
  const hasAttendance = subscription?.plan.features.includes("attendance");
  const hasFees = subscription?.plan.features.includes("fees");
  const hasExams = subscription?.plan.features.includes("exams");

  useEffect(() => {
    if (!enabled) return;
    const request =
      role === "parent" ? api<Child[]>("/api/me/children/") : api<Child>("/api/me/student/").then((c) => [c]);
    request.then(setChildren).catch(() => setChildren([]));
  }, [enabled, role]);

  if (!enabled || children === null) return null;
  if (children.length === 0) {
    return (
      <Card>
        <p className="text-sm text-slate-500">
          {role === "parent" ? "No children are linked to your login yet." : "Your student profile is not linked yet."} Please
          contact the institute.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="font-medium">{role === "parent" ? "My children" : "My profile"}</h2>
      <div className="space-y-4">
        {children.map((c) => (
          <div key={c.id} className="space-y-2">
            <Card>
              <p className="text-lg font-semibold">{c.full_name}</p>
              <p className="text-sm text-slate-500">Admission no {c.admission_no}</p>
              <p className="mt-2 text-sm">{enrollmentText(c.current_enrollment, terms.section)}</p>
              {c.current_enrollment && <p className="text-xs text-slate-500">Session {c.current_enrollment.session_name}</p>}
              {c.date_of_birth && <p className="text-xs text-slate-500">Born {formatDate(c.date_of_birth)}</p>}
            </Card>
            {hasAttendance && (
              <StudentAttendanceCard url={role === "parent" ? `/api/me/attendance/?student=${c.id}` : "/api/me/attendance/"} />
            )}
            {hasExams && <MyResultsCard student={role === "parent" ? c.id : undefined} />}
            {hasExams && <MyDateSheets url={role === "parent" ? `/api/me/exams/?student=${c.id}` : "/api/me/exams/"} />}
            {hasFees && <MyFeesCard url={role === "parent" ? `/api/me/invoices/?student=${c.id}` : "/api/me/invoices/"} />}
          </div>
        ))}
      </div>
    </div>
  );
}
