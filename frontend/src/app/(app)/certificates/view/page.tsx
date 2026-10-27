"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CertificateView } from "@/components/certificates/CertificateView";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Certificate } from "@/lib/certificates";
import { useInstitute } from "@/lib/useInstitute";

export default function CertificatePage() {
  const { user } = useAuth();
  const router = useRouter();
  const institute = useInstitute();
  const [cert, setCert] = useState<Certificate | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<Certificate>(`/api/certificates/${id}/`).then(setCert).catch(setError);
  }, []);

  async function cancel() {
    if (!cert || !window.confirm("Cancel this certificate? Its number will not be used again.")) return;
    try {
      await api(`/api/certificates/${cert.id}/`, { method: "DELETE" });
      router.push("/certificates/");
    } catch (err) {
      setError(err);
    }
  }

  if (!cert) return <ErrorBox error={error} />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href="/certificates/" className="text-sm text-indigo-600 hover:underline">
          ← Certificates
        </Link>
        <div className="flex items-center gap-3">
          <button onClick={cancel} className="text-sm text-red-600 hover:underline">
            Cancel certificate
          </button>
          <button onClick={() => window.print()} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white">
            Print / Save PDF
          </button>
        </div>
      </div>
      <ErrorBox error={error} />
      <CertificateView certificate={cert} tenant={user?.tenant} institute={institute ?? undefined} />
    </div>
  );
}
