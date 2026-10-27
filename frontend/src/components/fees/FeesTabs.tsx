"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/fees/", label: "Overview", match: (p: string) => p === "/fees" || p === "/fees/" },
  { href: "/fees/invoices/", label: "Invoices", match: (p: string) => p.startsWith("/fees/invoice") || p.startsWith("/fees/new") },
  { href: "/fees/setup/", label: "Fee setup", match: (p: string) => p.startsWith("/fees/setup") },
];

export function FeesTabs() {
  const pathname = usePathname();
  return (
    <div className="-mx-4 overflow-x-auto px-4 print:hidden">
      <div className="flex w-max gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className={`rounded-lg px-4 py-2 text-sm whitespace-nowrap ${
              t.match(pathname) ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
