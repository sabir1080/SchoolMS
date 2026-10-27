"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { StudentAttendanceCard } from "@/components/attendance/StudentAttendanceCard";
import { StudentFeesCard } from "@/components/fees/StudentFeesCard";
import { CreateLogin, usernameFrom } from "@/components/students/CreateLogin";
import { SectionPicker, type SectionChoice } from "@/components/students/SectionPicker";
import { StatusBadge } from "@/components/students/StatusBadge";
import { StudentPhoto } from "@/components/students/StudentPhoto";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/navigation";
import { enrollmentText, GENDERS, label, RELATIONS, type StudentDetail } from "@/lib/students";
import { termsFor } from "@/lib/terms";

export default function StudentViewPage() {
  const { user, subscription } = useAuth();
  const router = useRouter();
  const terms = termsFor(user?.tenant);
  const hasAttendance = subscription?.plan.features.includes("attendance");
  const hasFees = subscription?.plan.features.includes("fees");
  const [id, setId] = useState<string | null>(null);
  const [student, setStudent] = useState<StudentDetail | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [changing, setChanging] = useState(false);
  const [placement, setPlacement] = useState<SectionChoice>({ section: "", roll_number: "" });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setId(params.get("id"));
    setIsNew(params.get("new") === "1");
  }, []);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setStudent(await api<StudentDetail>(`/api/students/${id}/`));
    } catch (err) {
      setError(err);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (!student) return <ErrorBox error={error} />;
  const isAdmin = user?.role === "admin";

  async function saveClass(e: React.FormEvent) {
    e.preventDefault();
    if (!placement.section) return;
    setError(null);
    try {
      setStudent(
        await api<StudentDetail>(`/api/students/${student!.id}/enroll/`, {
          method: "POST",
          body: JSON.stringify({ section: Number(placement.section), roll_number: placement.roll_number }),
        }),
      );
      setChanging(false);
      setPlacement({ section: "", roll_number: "" });
    } catch (err) {
      setError(err);
    }
  }

  async function removeEnrollment(enrollmentId: number) {
    if (!confirm("Remove this class record?")) return;
    try {
      setStudent(await api<StudentDetail>(`/api/students/${student!.id}/enrollments/${enrollmentId}/`, { method: "DELETE" }));
    } catch (err) {
      setError(err);
    }
  }

  async function onDelete() {
    if (!confirm(`Delete ${student!.full_name} permanently? To keep the record, edit and mark as Left instead.`)) return;
    try {
      await api(`/api/students/${student!.id}/`, { method: "DELETE" });
      router.replace("/students");
    } catch (err) {
      setError(err);
    }
  }

  const info: [string, string][] = [
    ["Admission no", student.admission_no],
    ["Admission date", formatDate(student.admission_date)],
    ["Gender", label(GENDERS, student.gender)],
    ["Date of birth", student.date_of_birth ? formatDate(student.date_of_birth) : "—"],
    ["B-Form / CNIC", student.id_number || "—"],
    ["Blood group", student.blood_group || "—"],
    ["Phone", student.phone || "—"],
    ["Email", student.email || "—"],
    ["Previous school", student.previous_school || "—"],
    ["Address", student.address || "—"],
  ];

  return (
    <div className="max-w-3xl space-y-4">
      <Link href="/students" className="text-sm text-brand-600 hover:underline">
        ← All students
      </Link>
      {isNew && (
        <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          Admission saved. Admission number: <span className="font-semibold">{student.admission_no}</span>
        </p>
      )}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-4">
          <StudentPhoto student={student} editable={isAdmin} onChange={setStudent} />
          <div>
            <h1 className="text-2xl font-semibold">{student.full_name}</h1>
            <p className="text-sm text-slate-500">
              #{student.admission_no} · {enrollmentText(student.current_enrollment, terms.section)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={student.status} />
          {isAdmin && student.status === "active" && (
            <Link href={`/students/id-cards/?ids=${student.id}`} className="text-sm font-medium text-brand-600 hover:underline">
              ID card
            </Link>
          )}
          {isAdmin && subscription?.plan.features.includes("certificates") && (
            <Link href={`/certificates/?student=${student.id}`} className="text-sm font-medium text-brand-600 hover:underline">
              Certificate
            </Link>
          )}
          {isAdmin && (
            <Link href={`/students/edit/?id=${student.id}`}>
              <Button>Edit</Button>
            </Link>
          )}
        </div>
      </div>

      <ErrorBox error={error} />

      <Card>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
          {info.map(([k, v]) => (
            <div key={k} className={k === "Address" ? "col-span-2 sm:col-span-3" : ""}>
              <dt className="text-slate-500">{k}</dt>
              <dd className="font-medium break-words">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-medium">
            {terms.program} &amp; {terms.section.toLowerCase()}
          </h2>
          {isAdmin && (
            <button onClick={() => setChanging(!changing)} className="text-sm text-brand-600 hover:underline">
              {changing ? "Cancel" : student.current_enrollment ? `Change ${terms.program.toLowerCase()}` : `Assign ${terms.program.toLowerCase()}`}
            </button>
          )}
        </div>
        {changing && (
          <form onSubmit={saveClass} className="mt-3 space-y-3 rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
            <SectionPicker terms={terms} value={placement} onChange={setPlacement} allowSessionChoice />
            <Button type="submit" disabled={!placement.section}>
              Save
            </Button>
          </form>
        )}
        {student.enrollments.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Not assigned yet.</p>
        ) : (
          <ul className="mt-2 divide-y divide-slate-200 text-sm dark:divide-slate-800">
            {student.enrollments.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-2 py-2">
                <span>
                  <span className="font-medium">{e.session_name}</span>
                  {e.is_current && <span className="ml-1 text-xs text-emerald-600">(current)</span>} ·{" "}
                  {enrollmentText(e, terms.section)}
                </span>
                {isAdmin && (
                  <button onClick={() => removeEnrollment(e.id)} className="text-xs text-red-600 hover:underline">
                    Remove
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {hasAttendance && <StudentAttendanceCard url={`/api/attendance/students/${student.id}/`} />}
      {hasFees && isAdmin && <StudentFeesCard studentId={student.id} />}

      <Card>
        <h2 className="mb-2 font-medium">Parents / guardians</h2>
        {student.guardian_links.length === 0 && <p className="text-sm text-slate-500">No guardian added.</p>}
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {student.guardian_links.map(({ guardian: g, relation, is_primary }) => {
            const siblings = g.children.filter((c) => c.id !== student.id);
            return (
              <li key={g.id} className="py-3 text-sm">
                <p className="font-medium">
                  {g.name} <span className="font-normal text-slate-500">({label(RELATIONS, relation)})</span>
                  {is_primary && <span className="ml-2 text-xs text-emerald-600">Main contact</span>}
                </p>
                <p className="text-slate-500">
                  {g.phone ? (
                    <a href={`tel:${g.phone}`} className="text-brand-600 hover:underline">
                      {g.phone}
                    </a>
                  ) : (
                    "No phone"
                  )}
                  {g.cnic && ` · CNIC ${g.cnic}`}
                  {g.occupation && ` · ${g.occupation}`}
                </p>
                {siblings.length > 0 && (
                  <p className="text-slate-500">
                    Also parent of:{" "}
                    {siblings.map((c, i) => (
                      <span key={c.id}>
                        {i > 0 && ", "}
                        <Link href={`/students/view/?id=${c.id}`} onClick={() => setId(String(c.id))} className="text-brand-600 hover:underline">
                          {c.full_name}
                        </Link>
                      </span>
                    ))}
                  </p>
                )}
                <div className="mt-1">
                  {g.username ? (
                    <p className="text-xs text-slate-500">
                      Parent login: <span className="font-medium">{g.username}</span>
                    </p>
                  ) : (
                    isAdmin && (
                      <CreateLogin url={`/api/guardians/${g.id}/create-login/`} suggestedUsername={usernameFrom(g.name)} onCreated={load} />
                    )
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      <Card>
        <h2 className="mb-1 font-medium">Student login</h2>
        {student.username ? (
          <p className="text-sm text-slate-500">
            Username: <span className="font-medium">{student.username}</span>
            {student.status !== "active" && " (disabled while the student is not active)"}
          </p>
        ) : isAdmin ? (
          <>
            <p className="text-sm text-slate-500">Optional. Lets the student log in and see their profile.</p>
            <CreateLogin url={`/api/students/${student.id}/create-login/`} suggestedUsername={usernameFrom(student.full_name)} onCreated={load} />
          </>
        ) : (
          <p className="text-sm text-slate-500">No login.</p>
        )}
      </Card>

      {isAdmin && (
        <button onClick={onDelete} className="text-sm text-red-600 hover:underline">
          Delete student
        </button>
      )}
    </div>
  );
}
