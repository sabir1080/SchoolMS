"use client";

import { useEffect, useRef, useState } from "react";

import { BrandLogo } from "@/components/BrandLogo";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BRAND_COLORS, applyBrand, resizeLogo } from "@/lib/brand";

/** Institute logo and theme colour (white-label, Pro and Enterprise plans). */
export function BrandingSettings() {
  const { user, refreshUser } = useAuth();
  const brand = user?.tenant?.brand;
  const [logo, setLogo] = useState(brand?.logo ?? "");
  const [color, setColor] = useState(brand?.color ?? "indigo");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const savedHex = useRef(brand?.hex);
  savedHex.current = brand?.hex;

  // Preview the picked colour; go back to the saved one when leaving the page unsaved.
  useEffect(() => {
    applyBrand(BRAND_COLORS.find((c) => c.key === color)?.hex);
  }, [color]);
  useEffect(() => () => applyBrand(savedHex.current), []);

  if (!brand) return null;

  if (!brand.allowed) {
    return (
      <Card>
        <h2 className="font-medium">Logo and theme colour</h2>
        <p className="mt-1 text-sm text-slate-500">
          Show your own logo on the login page, menu, report cards and certificates, and pick your theme colour. Available
          on the Pro and Enterprise plans.
        </p>
      </Card>
    );
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    setMessage("");
    try {
      setLogo(await resizeLogo(file));
    } catch (err) {
      setError(err);
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      await api("/api/institute/settings/", { method: "PATCH", body: JSON.stringify({ logo, brand_color: color }) });
      await refreshUser();
      setMessage("Logo and colour saved.");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const changed = logo !== brand.logo || color !== brand.color;

  return (
    <Card>
      <h2 className="font-medium">Logo and theme colour</h2>
      <p className="mb-4 text-sm text-slate-500">
        Shown on the login page, menu, report cards, certificates and salary slips.
      </p>
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex h-20 w-20 items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
          {logo ? <BrandLogo src={logo} className="h-16 w-16" /> : <span className="text-xs text-slate-400">No logo</span>}
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            ref={fileInput}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={onFile}
            className="hidden"
            aria-label="Logo image"
          />
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
          >
            {logo ? "Change logo" : "Upload logo"}
          </button>
          {logo && (
            <button
              type="button"
              onClick={() => setLogo("")}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-red-600 dark:border-slate-700"
            >
              Remove logo
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 text-xs text-slate-500">PNG, JPG or WebP. A square logo looks best.</p>

      <p className="mt-5 mb-2 text-sm font-medium">Theme colour</p>
      <div className="flex flex-wrap gap-3" role="radiogroup" aria-label="Theme colour">
        {BRAND_COLORS.map((c) => (
          <button
            key={c.key}
            type="button"
            role="radio"
            aria-checked={color === c.key}
            aria-label={c.label}
            title={c.label}
            onClick={() => setColor(c.key)}
            className={`h-10 w-10 rounded-full ring-offset-2 dark:ring-offset-slate-900 ${
              color === c.key ? "ring-2 ring-slate-900 dark:ring-white" : ""
            }`}
            style={{ backgroundColor: c.hex }}
          />
        ))}
      </div>

      <div className="mt-5 space-y-3">
        <ErrorBox error={error} />
        {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
        <Button type="button" onClick={save} disabled={busy || !changed}>
          {busy ? "Saving…" : "Save logo and colour"}
        </Button>
      </div>
    </Card>
  );
}
