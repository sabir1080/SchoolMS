"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { startPayment, type PayOption } from "@/lib/payments";

const STYLES: Record<string, string> = {
  jazzcash: "bg-red-600 hover:bg-red-700 text-white",
  easypaisa: "bg-emerald-600 hover:bg-emerald-700 text-white",
  demo: "border border-slate-300 dark:border-slate-600",
};

/** "Pay with JazzCash / Easypaisa" buttons for one open bill. */
export function PayOnline({ invoiceId, compact = false }: { invoiceId: number; compact?: boolean }) {
  const { subscription } = useAuth();
  const router = useRouter();
  const [options, setOptions] = useState<PayOption[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const enabled = subscription?.is_usable && subscription.plan.features.includes("online_payments");

  useEffect(() => {
    if (enabled) api<PayOption[]>("/api/pay/options/").then(setOptions).catch(() => setOptions([]));
  }, [enabled]);

  if (!enabled || options.length === 0) return null;

  async function pay(provider: string) {
    setBusy(provider);
    setError(null);
    try {
      await startPayment(invoiceId, provider, (path) => router.push(path));
    } catch (err) {
      setError(err);
      setBusy(null);
    }
  }

  return (
    <div className="space-y-2">
      <div className={`flex flex-wrap gap-2 ${compact ? "" : "mt-1"}`}>
        {options.map((o) => (
          <button
            key={o.provider}
            type="button"
            onClick={() => pay(o.provider)}
            disabled={busy !== null}
            className={`rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-60 ${STYLES[o.provider]}`}
          >
            {busy === o.provider ? "Opening…" : o.provider === "demo" ? "Demo payment" : `Pay with ${o.label}`}
            {o.test_mode && o.provider !== "demo" && <span className="ml-1 text-xs opacity-80">(test)</span>}
          </button>
        ))}
      </div>
      <ErrorBox error={error} />
    </div>
  );
}
