"use client";

import { useEffect, useState } from "react";

import { ProgramsTab } from "@/components/academics/ProgramsTab";
import { SectionsTab } from "@/components/academics/SectionsTab";
import { SessionsTab } from "@/components/academics/SessionsTab";
import { SubjectsTab } from "@/components/academics/SubjectsTab";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";

const TABS = ["sessions", "programs", "sections", "subjects"] as const;
type Tab = (typeof TABS)[number];

export default function AcademicsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("sessions");

  // The tab lives in the URL (?tab=...) so it survives a refresh and can be linked to.
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("tab") as Tab | null;
    if (fromUrl && TABS.includes(fromUrl)) setTab(fromUrl);
  }, []);

  function goTo(next: string) {
    setTab(next as Tab);
    window.history.replaceState(null, "", `?tab=${next}`);
  }

  if (!user?.tenant) return null;
  if (user.role !== "admin") {
    return <p className="text-sm text-slate-500">Only institute admins can change the academic setup.</p>;
  }

  const terms = termsFor(user.tenant);
  const labels: Record<Tab, string> = {
    sessions: "Sessions",
    programs: terms.programs,
    sections: terms.sections,
    subjects: "Subjects",
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Academic setup</h1>
      <div className="-mx-4 overflow-x-auto px-4">
        <div className="flex w-max gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => goTo(t)}
              className={`rounded-lg px-4 py-2 text-sm whitespace-nowrap ${
                tab === t ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"
              }`}
            >
              {labels[t]}
            </button>
          ))}
        </div>
      </div>
      {tab === "sessions" && <SessionsTab />}
      {tab === "programs" && <ProgramsTab terms={terms} instituteType={user.tenant.institute_type} />}
      {tab === "sections" && <SectionsTab terms={terms} goTo={goTo} />}
      {tab === "subjects" && <SubjectsTab />}
    </div>
  );
}
