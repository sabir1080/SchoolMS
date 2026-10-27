import { formatMoney } from "./api";

export type InvoiceStatus = "unpaid" | "partial" | "paid" | "cancelled";

export interface FeeHead {
  id: number;
  name: string;
  frequency: "monthly" | "one_time";
  is_active: boolean;
  sort_order: number;
}

export interface InvoiceListItem {
  id: number;
  number: number;
  student: { id: number; full_name: string; admission_no: string; class_name: string | null };
  period: string;
  title: string;
  issue_date: string;
  due_date: string;
  total: string;
  paid: string;
  balance: string;
  status: InvoiceStatus;
}

export interface InvoiceDetail extends InvoiceListItem {
  session_name: string;
  notes: string;
  items: { id: number; description: string; amount: string; discount: string; net: string }[];
  payments: {
    id: number;
    receipt_number: number;
    amount: string;
    date: string;
    method: string;
    reference: string;
    received_by_name: string | null;
  }[];
}

export interface Discount {
  id: number;
  student: number;
  fee_head: number;
  fee_head_name: string;
  discount_type: "amount" | "percent";
  value: string;
  reason: string;
}

export const FREQUENCIES: [string, string][] = [
  ["monthly", "Every month"],
  ["one_time", "Once per session"],
];

export const PAYMENT_METHODS: [string, string][] = [
  ["cash", "Cash"],
  ["bank", "Bank deposit / transfer"],
  ["jazzcash", "JazzCash"],
  ["easypaisa", "Easypaisa"],
  ["card", "Card"],
  ["other", "Other"],
];

export const INVOICE_STATUS: Record<InvoiceStatus, { label: string; tone: string }> = {
  unpaid: { label: "Unpaid", tone: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300" },
  partial: { label: "Partly paid", tone: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200" },
  paid: { label: "Paid", tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" },
  cancelled: { label: "Cancelled", tone: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400" },
};

/** Common fees offered by "Add common fees". */
export const COMMON_FEES: { name: string; frequency: "monthly" | "one_time" }[] = [
  { name: "Tuition Fee", frequency: "monthly" },
  { name: "Admission Fee", frequency: "one_time" },
  { name: "Annual Charges", frequency: "one_time" },
  { name: "Exam Fee", frequency: "monthly" },
  { name: "Transport Fee", frequency: "monthly" },
];

export function invoiceNo(n: number) {
  return `INV-${String(n).padStart(4, "0")}`;
}

export function money(amount: string | number, currency: string | undefined) {
  return formatMoney(amount, currency || "PKR");
}

/** "2026-10" for the current month on this device, and the 1st/10th of it. */
export function monthDefaults() {
  const d = new Date();
  const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  return { month, issue: `${month}-01`, due: `${month}-10` };
}

export interface Receipt {
  id: number;
  receipt_number: number;
  amount: string;
  date: string;
  method: string;
  method_label: string;
  reference: string;
  received_by_name: string | null;
  student: {
    id: number;
    full_name: string;
    admission_no: string;
    class_name: string | null;
  };
  invoice: {
    id: number;
    number: number;
    title: string;
    total: string;
    paid_so_far: string;
    balance_after: string;
  };
  institute: { name: string; address: string; phone: string; currency: string };
}

export function receiptNo(n: number) {
  return `RCPT-${String(n).padStart(4, "0")}`;
}

const ONES = [
  "",
  "One",
  "Two",
  "Three",
  "Four",
  "Five",
  "Six",
  "Seven",
  "Eight",
  "Nine",
  "Ten",
  "Eleven",
  "Twelve",
  "Thirteen",
  "Fourteen",
  "Fifteen",
  "Sixteen",
  "Seventeen",
  "Eighteen",
  "Nineteen",
];
const TENS = [
  "",
  "",
  "Twenty",
  "Thirty",
  "Forty",
  "Fifty",
  "Sixty",
  "Seventy",
  "Eighty",
  "Ninety",
];

function belowThousand(n: number): string {
  const parts: string[] = [];
  if (n >= 100) parts.push(`${ONES[Math.floor(n / 100)]} Hundred`);
  const rest = n % 100;
  if (rest >= 20)
    parts.push(
      TENS[Math.floor(rest / 10)] + (rest % 10 ? `-${ONES[rest % 10]}` : ""),
    );
  else if (rest) parts.push(ONES[rest]);
  return parts.join(" ");
}

/** Whole amount in words: lakh/crore for PKR, INR and similar, thousand/million otherwise. */
export function amountInWords(
  amount: string | number,
  currency: string | undefined,
) {
  let n = Math.floor(Number(amount));
  if (!Number.isFinite(n) || n <= 0) return "Zero";
  const south = ["PKR", "INR", "BDT", "NPR", "LKR"].includes(currency ?? "PKR");
  const scales: [number, string][] = south
    ? [
        [10_000_000, "Crore"],
        [100_000, "Lakh"],
        [1000, "Thousand"],
      ]
    : [
        [1_000_000_000, "Billion"],
        [1_000_000, "Million"],
        [1000, "Thousand"],
      ];
  const parts: string[] = [];
  for (const [size, name] of scales) {
    if (n >= size) {
      const count = Math.floor(n / size);
      parts.push(
        `${size === 10_000_000 && count >= 1000 ? amountInWords(count, currency) : belowThousand(count)} ${name}`,
      );
      n %= size;
    }
  }
  if (n) parts.push(belowThousand(n));
  return parts.join(" ");
}
