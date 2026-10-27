"use client";

import { useEffect, useState } from "react";

import { ReceiptView } from "@/components/fees/ReceiptView";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Receipt } from "@/lib/fees";

export default function ReceiptPage() {
  const { user } = useAuth();
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<Receipt>(`/api/fees/receipts/${id}/`).then(setReceipt).catch(setError);
  }, []);

  if (!receipt) return <ErrorBox error={error} />;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <button onClick={() => history.back()} className="text-sm text-brand-600 hover:underline">
          ← Back
        </button>
        <button onClick={() => window.print()} className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white">
          Print / Save PDF
        </button>
      </div>
      <ReceiptView receipt={receipt} tenant={user?.tenant} />
    </div>
  );
}
