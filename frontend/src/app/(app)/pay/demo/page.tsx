"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/fees";
import type { OnlinePayment } from "@/lib/payments";

/** A pretend gateway so admins can try the whole online payment flow without a merchant account. */
export default function DemoGatewayPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [payment, setPayment] = useState<OnlinePayment | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get("ref");
    api<OnlinePayment>(`/api/pay/status/?ref=${encodeURIComponent(ref ?? "")}`).then(setPayment).catch(setError);
  }, []);

  async function finish(outcome: "success" | "cancel") {
    if (!payment) return;
    setBusy(true);
    try {
      await api("/api/pay/demo/complete/", { method: "POST", body: JSON.stringify({ reference: payment.reference, outcome }) });
      router.replace(`/pay/result/?ref=${payment.reference}`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  if (!payment) return <ErrorBox error={error} />;

  return (
    <div className="mx-auto max-w-md space-y-4">
      <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
        Demo gateway — no real money moves. Use it to see how online payment works before your JazzCash or Easypaisa
        account is ready. A successful demo adds a real payment to the bill (you can delete it from the bill).
      </p>
      <Card>
        <p className="text-sm text-slate-500">Paying</p>
        <p className="text-3xl font-semibold">{money(payment.amount, user?.tenant?.currency)}</p>
        <p className="mt-1 text-sm">
          {payment.invoice_title} · {payment.student}
        </p>
        <p className="text-xs text-slate-500">Reference {payment.reference}</p>
        <ErrorBox error={error} />
        <div className="mt-4 flex gap-3">
          <Button onClick={() => finish("success")} disabled={busy || payment.status !== "pending"}>
            Pay now (demo)
          </Button>
          <button onClick={() => finish("cancel")} disabled={busy || payment.status !== "pending"} className="text-sm text-red-600">
            Cancel
          </button>
        </div>
      </Card>
    </div>
  );
}
