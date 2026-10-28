"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { AGREEMENT_TONE, type Agreement } from "@/lib/agreements";
import { formatDate } from "@/lib/navigation";

/** An institute's agreements, for the platform owner's Manage panel. */
export function TenantAgreements({ tenantId }: { tenantId: number }) {
  const [agreements, setAgreements] = useState<Agreement[] | null>(null);

  useEffect(() => {
    api<Agreement[]>(`/api/platform/agreements/?tenant=${tenantId}`).then(setAgreements).catch(() => setAgreements([]));
  }, [tenantId]);

  if (!agreements) return null;
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium">Agreements</h3>
      {agreements.length === 0 ? (
        <p className="text-sm text-amber-700">No agreement signed yet.</p>
      ) : (
        <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
          {agreements.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                {a.number} · {a.kind === "trial" ? "Free trial" : `${a.plan_name} (${a.billing_cycle})`} · signed {formatDate(a.signed_at)} by {a.signer_name}
              </span>
              <span className="flex items-center gap-3">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${AGREEMENT_TONE[a.status]}`}>{a.status_label}</span>
                <Link href={`/platform/agreement/?id=${a.id}`} className="text-brand-600 hover:underline">
                  View
                </Link>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
