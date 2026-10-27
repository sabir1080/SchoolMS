"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BrandLogo } from "@/components/BrandLogo";
import { InstallApp } from "@/components/InstallApp";
import { useAuth } from "@/lib/auth";
import { ALWAYS_OPEN, NAV_BY_ROLE, ROLE_LABELS } from "@/lib/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, subscription, loading, unreachable, retry, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const locked = Boolean(user?.tenant && subscription && !subscription.is_usable);

  useEffect(() => {
    if (!loading && !user && !unreachable) router.replace("/login");
  }, [user, loading, unreachable, router]);

  useEffect(() => {
    // An expired institute can only see the billing and account pages.
    if (locked && !ALWAYS_OPEN.some((path) => pathname.startsWith(path))) router.replace("/billing");
  }, [locked, pathname, router]);

  if (!user && unreachable && !loading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="max-w-sm rounded-2xl bg-white p-6 text-center shadow-sm dark:bg-slate-900">
          <p className="font-semibold">Cannot reach the server</p>
          <p className="mt-1 text-sm text-slate-500">Check your internet connection. You are still logged in.</p>
          <button onClick={retry} className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white">
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!user) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">Loading…</div>;
  }

  const features = subscription?.plan.features ?? [];
  const nav = locked
    ? NAV_BY_ROLE[user.role].filter((item) => ALWAYS_OPEN.includes(item.href))
    : NAV_BY_ROLE[user.role].filter((item) => !item.feature || features.includes(item.feature));

  function onLogout() {
    const wasPlatform = user?.role === "super_admin";
    logout();
    router.replace(wasPlatform ? "/platform/login" : "/login");
  }

  return (
    <div className="min-h-screen md:flex">
      <header className="flex items-center justify-between border-b print:hidden border-slate-200 bg-white px-4 py-3 md:hidden dark:border-slate-800 dark:bg-slate-900">
        <span className="flex min-w-0 items-center gap-2">
          <BrandLogo src={user.tenant?.brand?.logo} className="h-8 w-8" />
          <span className="truncate font-semibold">{user.tenant?.name ?? "SchoolMS Platform"}</span>
        </span>
        <button
          onClick={() => setMenuOpen((open) => !open)}
          className="rounded-lg border border-slate-300 px-3 py-1 text-sm dark:border-slate-700"
          aria-expanded={menuOpen}
        >
          Menu
        </button>
      </header>

      <aside
        className={`${menuOpen ? "block" : "hidden"} print:hidden border-b border-slate-200 bg-white md:block md:min-h-screen md:w-60 md:shrink-0 md:border-r md:border-b-0 dark:border-slate-800 dark:bg-slate-900`}
      >
        <div className="hidden items-center gap-3 px-5 py-5 md:flex">
          <BrandLogo src={user.tenant?.brand?.logo} className="h-10 w-10" />
          <div className="min-w-0">
            <p className="font-semibold">{user.tenant?.name ?? "SchoolMS Platform"}</p>
            <p className="text-xs text-slate-500">{ROLE_LABELS[user.role]}</p>
          </div>
        </div>
        <nav className="space-y-1 px-3 py-3 md:py-0">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className={`block rounded-lg px-3 py-2 text-sm ${
                pathname.startsWith(item.href)
                  ? "bg-brand-50 font-medium text-brand-700 dark:bg-brand-950 dark:text-brand-300"
                  : "hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
          <InstallApp />
          <button
            onClick={onLogout}
            className="block w-full rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
            Log out
          </button>
        </nav>
      </aside>

      <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
    </div>
  );
}
