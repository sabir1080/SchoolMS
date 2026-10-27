"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function ExamsTabs() {
  const pathname = usePathname();
  const tabs = [
    { href: "/exams/", label: "Exams", active: !pathname.includes("/grading") && !pathname.includes("/combined") },
    { href: "/exams/combined/", label: "Annual result", active: pathname.includes("/combined") },
    { href: "/exams/grading/", label: "Grading", active: pathname.includes("/grading") },
  ];
  return (
    <div className="flex w-max max-w-full gap-1 overflow-x-auto rounded-xl bg-slate-200/60 p-1 print:hidden dark:bg-slate-800">
      {tabs.map((t) => (
        <Link
          key={t.href}
          href={t.href}
          className={`rounded-lg px-3 py-2 text-sm whitespace-nowrap sm:px-4 ${t.active ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"}`}
        >
          {t.label}
        </Link>
      ))}
    </div>
  );
}

export function ExamStatusBadge({ label, tone }: { label: string; tone: string }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${tone}`}>{label}</span>;
}
