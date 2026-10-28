"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AgreementDocument } from "@/components/agreements/AgreementDocument";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import type { Agreement } from "@/lib/agreements";

export default function AgreementPage() {
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<Agreement>(`/api/agreements/${id}/`).then(setAgreement).catch(setError);
  }, []);

  if (!agreement) return <ErrorBox error={error} />;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <Link href="/billing/" className="text-sm text-brand-600 hover:underline">
          ← Plan &amp; Billing
        </Link>
        <button onClick={() => window.print()} className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white">
          Print / Save PDF
        </button>
      </div>
      <AgreementDocument agreement={agreement} />
    </div>
  );
}
