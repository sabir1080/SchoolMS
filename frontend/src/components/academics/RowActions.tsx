"use client";

import { api } from "@/lib/api";

/** Edit / Delete links used by every academics list row. */
export function RowActions({
  editing,
  onEdit,
  deleteUrl,
  name,
  onDeleted,
  onError,
}: {
  editing: boolean;
  onEdit: () => void;
  deleteUrl: string;
  name: string;
  onDeleted: () => void;
  onError: (err: unknown) => void;
}) {
  async function onDelete() {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await api(deleteUrl, { method: "DELETE" });
      onDeleted();
    } catch (err) {
      onError(err);
    }
  }

  return (
    <div className="flex shrink-0 gap-3 text-sm">
      <button onClick={onEdit} className="text-indigo-600 hover:underline">
        {editing ? "Close" : "Edit"}
      </button>
      <button onClick={onDelete} className="text-red-600 hover:underline">
        Delete
      </button>
    </div>
  );
}

export function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "green" | "red" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    green: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    red: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
  };
  return <span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}
