"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { AcademicSession, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import {
  IdCard,
  type IdCardData,
  type IdCardInstitute,
} from "@/components/students/IdCard";
import { Card, ErrorBox, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";
import { useLatestRequest } from "@/lib/useLatestRequest";

export default function IdCardsPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const current = sessions.items.find((s) => s.is_current);
  const sections = useList<Section>(
    current ? `/api/academics/sections/?session=${current.id}` : null,
  );
  const [ids, setIds] = useState<string | null>(null);
  const [section, setSection] = useState("");
  const [data, setData] = useState<{
    institute: IdCardInstitute;
    cards: IdCardData[];
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const latest = useLatestRequest();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setIds(params.get("ids") ?? "");
    setSection(params.get("section") ?? "");
  }, []);

  useEffect(() => {
    if (ids === null) return;
    const query = ids
      ? `ids=${encodeURIComponent(ids)}`
      : section
        ? `section=${section}`
        : "";
    setData(null);
    setError(null);
    if (query)
      latest(
        api<{ institute: IdCardInstitute; cards: IdCardData[] }>(
          `/api/students/id-cards/?${query}`,
        ),
        setData,
        setError,
      );
  }, [ids, section, latest]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <Link
            href="/students"
            className="text-sm text-brand-600 hover:underline"
          >
            ← Students
          </Link>
          <h1 className="text-2xl font-semibold">Student ID cards</h1>
        </div>
        {data && data.cards.length > 0 && (
          <button
            onClick={() => window.print()}
            className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white"
          >
            Print / Save PDF
          </button>
        )}
      </div>

      {!ids && (
        <div className="print:hidden">
          <Card>
            <div className="max-w-xs">
              <SelectField
                label={`${terms.program} - ${terms.section}`}
                options={[
                  ["", "Choose…"],
                  ...sections.items.map((s): [string, string] => [
                    String(s.id),
                    `${s.program_name} - ${s.name}`,
                  ]),
                ]}
                value={section}
                onChange={(e) => setSection(e.target.value)}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Each card prints at the standard size (85.6 × 54 mm), front and
              back side by side: cut, fold and laminate. Add photos from each
              student&apos;s page.
            </p>
          </Card>
        </div>
      )}

      <ErrorBox error={error} />
      {data &&
        (data.cards.length === 0 ? (
          <Card>
            <p className="text-sm text-slate-500">No active students here.</p>
          </Card>
        ) : (
          <div className="id-card-sheet space-y-[4mm] overflow-x-auto pb-2">
            <p className="text-sm text-slate-500 print:hidden">
              {data.cards.length} card{data.cards.length === 1 ? "" : "s"}
              {data.cards.some((c) => !c.photo) &&
                ` · ${data.cards.filter((c) => !c.photo).length} without a photo`}
            </p>
            {data.cards.map((card) => (
              <IdCard
                key={card.id}
                card={card}
                institute={data.institute}
                logo={user?.tenant?.brand?.logo}
                classLabel={terms.program}
              />
            ))}
          </div>
        ))}
    </div>
  );
}
