"use client";

import { useEffect, useState } from "react";

import { StudentForm } from "@/components/students/StudentForm";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { StudentDetail } from "@/lib/students";

export default function EditStudentPage() {
  const { user } = useAuth();
  const [student, setStudent] = useState<StudentDetail | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<StudentDetail>(`/api/students/${id}/`).then(setStudent).catch(setError);
  }, []);

  if (user?.role !== "admin") return <p className="text-sm text-slate-500">Only institute admins can edit students.</p>;
  if (!student) return <ErrorBox error={error} />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Edit {student.full_name}</h1>
      <StudentForm student={student} />
    </div>
  );
}
