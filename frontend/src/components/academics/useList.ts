"use client";

import { useCallback, useEffect, useState } from "react";

import { apiList } from "@/lib/api";

/** Load a list endpoint and reload it on demand. */
export function useList<T>(path: string | null) {
  const [items, setItems] = useState<T[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      setItems(await apiList<T>(path));
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoaded(true);
    }
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { items, loaded, error, reload };
}
