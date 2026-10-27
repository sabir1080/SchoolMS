"use client";

import { StudentForm } from "@/components/students/StudentForm";
import { useAuth } from "@/lib/auth";

export default function NewStudentPage() {
  const { user } = useAuth();
  if (user?.role !== "admin") return <p className="text-sm text-slate-500">Only institute admins can admit students.</p>;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">New admission</h1>
      <StudentForm />
    </div>
  );
}
