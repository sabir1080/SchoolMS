"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function AttendanceTabs() {
  const pathname = usePathname();
  const tabs = [
    { href: "/attendance/", label: "Take attendance", active: !pathname.includes("/report") },
    { href: "/attendance/report/", label: "Monthly report", active: pathname.includes("/report") },
  ];
  return (
    <div className="flex w-max gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800">
      {tabs.map((t) => (
        <Link
          key={t.href}
          href={t.href}
          className={`rounded-lg px-4 py-2 text-sm whitespace-nowrap ${
            t.active ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"
          }`}
        >
          {t.label}
        </Link>
      ))}
    </div>
  );
}
