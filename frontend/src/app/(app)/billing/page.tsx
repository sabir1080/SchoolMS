"use client";

import { useEffect, useState } from "react";

import { BillingAgreements } from "@/components/agreements/BillingAgreements";
import { DataBackupCard } from "@/components/backups/DataBackupCard";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api, formatMoney, type Plan, type PlanPrice } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, STATUS_LABELS } from "@/lib/navigation";

function priceFor(plan: Plan, currency: string, cycle: PlanPrice["billing_cycle"]) {
  return (
    plan.prices.find((p) => p.currency === currency && p.billing_cycle === cycle) ??
    plan.prices.find((p) => p.currency === "USD" && p.billing_cycle === cycle)
  );
}

function limitText(limit: number | null) {
  return limit === null ? "Unlimited" : String(limit);
}

export default function BillingPage() {
  const { user, subscription, refreshSubscription } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [choose, setChoose] = useState<string | null>(null);

  function pick(code: string) {
    setChoose(code);
    setTimeout(() => document.getElementById("agreements")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  useEffect(() => {
    refreshSubscription();
    api<Plan[]>("/api/public/plans/").then(setPlans).catch(setError);
    // Load once when the page opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!user?.tenant) return null;

  if (user.role !== "admin") {
    return (
      <Card>
        <h1 className="text-xl font-semibold">Subscription</h1>
        <p className="mt-2 text-sm text-slate-500">
          {subscription?.is_usable
            ? "Your institute's subscription is active."
            : "Your institute's subscription has expired. Please contact your institute admin."}
        </p>
      </Card>
    );
  }

  const currency = user.tenant.currency;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Plan &amp; Billing</h1>
      <ErrorBox error={error} />

      {subscription && (
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm text-slate-500">Current plan</p>
              <p className="text-xl font-semibold">{subscription.plan.name}</p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                subscription.is_usable
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
              }`}
            >
              {STATUS_LABELS[subscription.effective_status]}
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-slate-500">{subscription.is_usable ? "Valid until" : "Ended on"}</dt>
              <dd className="font-medium">{formatDate(subscription.current_period_end)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Days left</dt>
              <dd className="font-medium">{subscription.days_left}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Students</dt>
              <dd className="font-medium">
                {subscription.usage.students} / {limitText(subscription.plan.max_students)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Staff</dt>
              <dd className="font-medium">
                {subscription.usage.staff} / {limitText(subscription.plan.max_staff)}
              </dd>
            </div>
          </dl>
          {!subscription.is_usable && (
            <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              Your subscription has expired, so other pages are locked. Renew to continue using SchoolMS.
            </p>
          )}
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => {
          const monthly = priceFor(plan, currency, "monthly");
          const yearly = priceFor(plan, currency, "yearly");
          const current = subscription?.plan.code === plan.code;
          return (
            <Card key={plan.code}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{plan.name}</h2>
                {current && <span className="text-xs font-medium text-brand-600">Current</span>}
              </div>
              <p className="text-sm text-slate-500">{plan.description}</p>
              {monthly && (
                <p className="mt-3 text-2xl font-semibold">
                  {formatMoney(monthly.amount, monthly.currency)}
                  <span className="text-sm font-normal text-slate-500"> / month</span>
                </p>
              )}
              {yearly && (
                <p className="text-xs text-slate-500">or {formatMoney(yearly.amount, yearly.currency)} / year</p>
              )}
              <ul className="mt-3 space-y-1 text-sm">
                <li>Students: {limitText(plan.max_students)}</li>
                <li>Staff: {limitText(plan.max_staff)}</li>
                {plan.feature_labels.map((label) => (
                  <li key={label}>✓ {label}</li>
                ))}
              </ul>
              <Button type="button" onClick={() => pick(plan.code)} className="mt-4 w-full">
                {current && subscription?.effective_status !== "trialing" ? `Renew ${plan.name}` : `Choose ${plan.name}`}
              </Button>
            </Card>
          );
        })}
      </div>

      <Card>
        <h2 className="font-medium">How to upgrade or renew</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
          <li>Tap Choose (or Renew) on a plan and pick monthly or yearly.</li>
          <li>Fill in your details, read the subscription agreement and sign it by typing your name.</li>
          <li>Pay by bank transfer, JazzCash or Easypaisa using the details shown, and add the payment reference.</li>
          <li>We confirm the payment, your plan starts, and the agreement shows as Active with the paid period.</li>
        </ol>
      </Card>

      <div id="agreements" className="scroll-mt-4">
        <BillingAgreements plans={plans} choose={choose} onChosen={() => setChoose(null)} />
      </div>

      {!subscription?.is_usable && <DataBackupCard />}
    </div>
  );
}
