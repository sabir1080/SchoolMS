"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth";
import { NAV_BY_ROLE, ROLE_LABELS } from "@/lib/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (!user) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">Loading…</div>;
  }

  const nav = NAV_BY_ROLE[user.role];

  return (
    <div className="min-h-screen md:flex">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden dark:border-slate-800 dark:bg-slate-900">
        <span className="font-semibold">{user.tenant?.name ?? "SchoolMS"}</span>
        <button
          onClick={() => setMenuOpen((open) => !open)}
          className="rounded-lg border border-slate-300 px-3 py-1 text-sm dark:border-slate-700"
          aria-expanded={menuOpen}
        >
          Menu
        </button>
      </header>

      <aside
        className={`${menuOpen ? "block" : "hidden"} border-b border-slate-200 bg-white md:block md:min-h-screen md:w-60 md:shrink-0 md:border-r md:border-b-0 dark:border-slate-800 dark:bg-slate-900`}
      >
        <div className="hidden px-5 py-5 md:block">
          <p className="font-semibold">{user.tenant?.name ?? "SchoolMS"}</p>
          <p className="text-xs text-slate-500">{ROLE_LABELS[user.role]}</p>
        </div>
        <nav className="space-y-1 px-3 py-3 md:py-0">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className={`block rounded-lg px-3 py-2 text-sm ${
                pathname.startsWith(item.href)
                  ? "bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                  : "hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
          <button
            onClick={logout}
            className="block w-full rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
            Log out
          </button>
        </nav>
      </aside>

      <main className="flex-1 p-4 md:p-8">{children}</main>
    </div>
  );
}
