"use client";

import { useEffect, useState } from "react";

import { expiredNotice } from "@/lib/api";

/** "Your login has expired" on the login page after the app sent the user back there. */
export function ExpiredNotice() {
  const [show, setShow] = useState(false);
  useEffect(() => setShow(expiredNotice.take() !== null), []);
  if (!show) return null;
  return (
    <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
      Your login has expired. Please sign in again.
    </p>
  );
}
