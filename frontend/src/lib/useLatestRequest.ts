"use client";

import { useCallback, useRef } from "react";

/**
 * Runs requests so that only the newest one's answer is used. When the user switches a filter (or an
 * action reloads the list) while an older request is still on its way, the older answer is dropped.
 */
export function useLatestRequest() {
  const latest = useRef(0);
  return useCallback(<T>(request: Promise<T>, onData: (data: T) => void, onError: (error: unknown) => void) => {
    const id = ++latest.current;
    request.then(
      (data) => id === latest.current && onData(data),
      (error) => id === latest.current && onError(error),
    );
  }, []);
}
