"use client";

import { useState } from "react";

import { useInstallApp } from "@/lib/pwa";

/** "Install app" for Android/desktop Chrome and Edge; on iPhone a short "Add to Home Screen" hint. */
export function InstallApp({ className = "" }: { className?: string }) {
  const { state, install } = useInstallApp();
  const [hint, setHint] = useState(false);
  if (state === "hidden") return null;
  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => (state === "prompt" ? install() : setHint(!hint))}
        className="block w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-950"
      >
        Install app on this phone
      </button>
      {hint && (
        <p className="px-3 pb-2 text-xs text-slate-500">
          In Safari, tap the Share button, then &ldquo;Add to Home Screen&rdquo;.
        </p>
      )}
    </div>
  );
}
