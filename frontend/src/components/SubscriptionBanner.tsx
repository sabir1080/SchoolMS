"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

/** Reminds institute users when the trial is ending or the subscription has lapsed. */
export function SubscriptionBanner() {
  const { user, subscription } = useAuth();
  if (!user?.tenant || !subscription) return null;

  const isAdmin = user.role === "admin";
  let message: string | null = null;
  if (!subscription.is_usable) {
    message = "Your institute's subscription has expired.";
  } else if (subscription.effective_status === "trialing") {
    message = `Free trial: ${subscription.days_left} day${subscription.days_left === 1 ? "" : "s"} left.`;
  } else if (subscription.days_left <= 7) {
    message = `Your subscription ends in ${subscription.days_left} day${subscription.days_left === 1 ? "" : "s"}. Renew from Plan & Billing.`;
  }
  if (!message) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
      <span>{message}</span>
      {isAdmin ? (
        <Link href="/billing" className="font-medium underline">
          View plans
        </Link>
      ) : (
        !subscription.is_usable && <span>Please contact your institute admin.</span>
      )}
    </div>
  );
}
