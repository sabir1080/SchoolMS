"use client";

import { TodayCard } from "@/components/attendance/TodayCard";
import { SetupChecklist } from "@/components/SetupChecklist";
import { PortalCards } from "@/components/students/PortalCards";
import { SubscriptionBanner } from "@/components/SubscriptionBanner";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/navigation";

export default function DashboardPage() {
  const { user } = useAuth();
  if (!user) return null;

  const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;

  return (
    <div className="space-y-6">
      <SubscriptionBanner />
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {name}</h1>
        <p className="text-sm text-slate-500">
          {ROLE_LABELS[user.role]}
          {user.tenant && ` · ${user.tenant.name}`}
        </p>
      </div>
      <SetupChecklist />
      <TodayCard />
      <PortalCards />
      {(user.role === "admin" || user.role === "teacher") && (
        <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
          Fee summaries will appear here once the fees module is added.
        </div>
      )}
    </div>
  );
}
