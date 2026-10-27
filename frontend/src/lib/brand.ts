import { resizeImage } from "./images";

/** White-label branding: the institute's logo and theme colour (Pro and Enterprise plans). */

export interface Brand {
  logo: string;
  color: string;
  hex: string;
  /** Whether the institute's plan lets it change the logo and colour. */
  allowed: boolean;
}

export const DEFAULT_BRAND_HEX = "#4f46e5";

/** Theme colours an institute can pick; keep in sync with backend `apps.tenants.branding.BRAND_COLORS`. */
export const BRAND_COLORS: { key: string; label: string; hex: string }[] = [
  { key: "indigo", label: "Indigo", hex: "#4f46e5" },
  { key: "blue", label: "Blue", hex: "#1d4ed8" },
  { key: "teal", label: "Teal", hex: "#0f766e" },
  { key: "green", label: "Green", hex: "#15803d" },
  { key: "purple", label: "Purple", hex: "#7e22ce" },
  { key: "rose", label: "Rose", hex: "#be123c" },
  { key: "orange", label: "Orange", hex: "#c2410c" },
  { key: "slate", label: "Slate", hex: "#334155" },
];

/** Set the page's theme colour (the `brand-*` Tailwind colours derive from it). */
export function applyBrand(hex: string | null | undefined) {
  if (typeof document === "undefined") return;
  const value = hex && /^#[0-9a-f]{6}$/i.test(hex) ? hex : DEFAULT_BRAND_HEX;
  document.documentElement.style.setProperty("--brand", value);
}

/** Shrink an uploaded logo to at most 256px and return it as a small data URL. */
export function resizeLogo(file: File): Promise<string> {
  return resizeImage(file, 256, 190_000, true);
}
