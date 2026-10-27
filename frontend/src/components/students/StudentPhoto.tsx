"use client";

import { useRef, useState } from "react";

import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { resizeImage } from "@/lib/images";
import type { StudentDetail } from "@/lib/students";

/** The student's photo (for the profile and ID card); admins can add, change or remove it. */
export function StudentPhoto({
  student,
  editable,
  onChange,
}: {
  student: StudentDetail;
  editable: boolean;
  onChange: (student: StudentDetail) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const initials = (student.first_name[0] ?? "") + (student.last_name[0] ?? "");

  async function save(photo: string) {
    setBusy(true);
    setError(null);
    try {
      onChange(
        await api<StudentDetail>(`/api/students/${student.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ photo }),
        }),
      );
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      await save(await resizeImage(file, 300, 130_000));
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      {student.photo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={student.photo}
          alt={`Photo of ${student.full_name}`}
          className="h-20 w-20 rounded-xl object-cover"
        />
      ) : (
        <div className="flex h-20 w-20 items-center justify-center rounded-xl bg-brand-50 text-xl font-semibold text-brand-700 uppercase dark:bg-brand-950">
          {initials}
        </div>
      )}
      {editable && (
        <div className="flex gap-2 text-xs">
          <input
            ref={input}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={onFile}
            className="hidden"
            aria-label="Student photo"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => input.current?.click()}
            className="text-brand-600 hover:underline"
          >
            {busy ? "Saving…" : student.photo ? "Change photo" : "Add photo"}
          </button>
          {student.photo && !busy && (
            <button
              type="button"
              onClick={() => save("")}
              className="text-red-600 hover:underline"
            >
              Remove
            </button>
          )}
        </div>
      )}
      <ErrorBox error={error} />
    </div>
  );
}
