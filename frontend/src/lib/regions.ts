/** Countries offered on sign-up with their usual currency. Others can be added any time. */
export const COUNTRIES: { code: string; name: string; currency: string }[] = [
  { code: "PK", name: "Pakistan", currency: "PKR" },
  { code: "AE", name: "United Arab Emirates", currency: "AED" },
  { code: "SA", name: "Saudi Arabia", currency: "SAR" },
  { code: "QA", name: "Qatar", currency: "QAR" },
  { code: "OM", name: "Oman", currency: "OMR" },
  { code: "KW", name: "Kuwait", currency: "KWD" },
  { code: "BH", name: "Bahrain", currency: "BHD" },
  { code: "IN", name: "India", currency: "INR" },
  { code: "BD", name: "Bangladesh", currency: "BDT" },
  { code: "AF", name: "Afghanistan", currency: "AFN" },
  { code: "GB", name: "United Kingdom", currency: "GBP" },
  { code: "US", name: "United States", currency: "USD" },
  { code: "CA", name: "Canada", currency: "CAD" },
  { code: "AU", name: "Australia", currency: "AUD" },
  { code: "MY", name: "Malaysia", currency: "MYR" },
  { code: "TR", name: "Türkiye", currency: "TRY" },
];

export function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Karachi";
  } catch {
    return "Asia/Karachi";
  }
}

/** Turn an institute name into a suggested code, e.g. "Al-Huda School" -> "al-huda-school". */
export function suggestCode(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 30)
    .replace(/-+$/, "");
}
