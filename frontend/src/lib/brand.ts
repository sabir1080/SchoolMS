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

const LOGO_SIZE = 256;

/** Shrink an uploaded image to at most 256px and return it as a small data URL. */
export function resizeLogo(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      reject(new Error("Please choose a PNG, JPG or WebP image."));
      return;
    }
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const scale = Math.min(1, LOGO_SIZE / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(img.width * scale));
      canvas.height = Math.max(1, Math.round(img.height * scale));
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("Could not read this image."));
        return;
      }
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      // PNG keeps transparent backgrounds; fall back to JPEG if it is too large.
      let data = canvas.toDataURL("image/png");
      if (data.length > 190_000) data = canvas.toDataURL("image/jpeg", 0.85);
      resolve(data);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read this image."));
    };
    img.src = url;
  });
}
