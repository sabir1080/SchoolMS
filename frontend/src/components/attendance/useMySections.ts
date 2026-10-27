"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { MySection } from "@/lib/attendance";

/** Sections the user can take attendance for (current session). */
export function useMySections() {
  const [sections, setSections] = useState<MySection[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const reload = useCallback(() => {
    api<MySection[]>("/api/attendance/sections/").then(setSections).catch((err) => {
      setError(err);
      setSections([]);
    });
  }, []);

  useEffect(reload, [reload]);
  return { sections, error, reload };
}
