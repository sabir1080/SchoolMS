export type CertificateKind = "character" | "leaving" | "bonafide";

export interface CertificateData {
  full_name: string;
  gender: string;
  father_name: string;
  relation: string;
  admission_no: string;
  admission_date: string | null;
  date_of_birth: string | null;
  class_name: string;
  program_name: string;
  roll_number: string;
  session_name: string;
  conduct?: string;
  purpose?: string;
  leaving_date?: string;
  reason?: string;
  remarks?: string;
}

export interface Certificate {
  id: number;
  student: number;
  kind: CertificateKind;
  kind_label: string;
  number: number;
  issued_on: string;
  data: CertificateData;
}

export const KINDS: { value: CertificateKind; title: string; about: string }[] = [
  { value: "character", title: "Character certificate", about: "Conduct and character of a current or former student." },
  { value: "leaving", title: "School leaving certificate", about: "When a student leaves: date, reason, conduct." },
  { value: "bonafide", title: "Bonafide certificate", about: "Proof that the student studies here (for passport, bank, scholarship…)." },
];

export function certificateNo(n: number) {
  return `CERT-${String(n).padStart(4, "0")}`;
}

/** "11 May 2016". */
export function longDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

const ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
  "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
const TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];
const ORDINAL_ONES = ["", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth", "Eleventh",
  "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth"];

function below100(n: number) {
  return n < 20 ? ONES[n] : `${TENS[Math.floor(n / 10)]}${n % 10 ? `-${ONES[n % 10]}` : ""}`;
}

function yearWords(y: number) {
  if (y >= 2000) return `Two Thousand${y % 1000 ? ` ${y % 1000 >= 100 ? `${ONES[Math.floor((y % 1000) / 100)]} Hundred ` : ""}${below100(y % 100)}` : ""}`.trim();
  return `${below100(Math.floor(y / 100))} ${y % 100 ? below100(y % 100) : "Hundred"}`;
}

/** Date of birth in words, as written on Pakistani certificates: "Eleventh May, Two Thousand Sixteen". */
export function dateInWords(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  const day = d.getDate();
  const dayWord = day < 20 ? ORDINAL_ONES[day] : day % 10 === 0 ? `${TENS[day / 10].slice(0, -1)}ieth` : `${TENS[Math.floor(day / 10)]}-${ORDINAL_ONES[day % 10]}`;
  return `${dayWord} ${d.toLocaleDateString("en-GB", { month: "long" })}, ${yearWords(d.getFullYear())}`;
}

export function pronouns(gender: string) {
  if (gender === "female") return { he: "she", He: "She", his: "her", His: "Her", him: "her", child: "daughter" };
  if (gender === "male") return { he: "he", He: "He", his: "his", His: "His", him: "him", child: "son" };
  return { he: "they", He: "They", his: "their", His: "Their", him: "them", child: "child" };
}
