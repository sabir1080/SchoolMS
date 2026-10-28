export interface AgreementProvider {
  business_name: string;
  owner_name: string;
  address: string;
  phone: string;
  email: string;
  grace_days: number;
  data_retention_days: number;
  refund_policy: string;
}

export interface AgreementSchedule {
  plan?: string;
  plan_code?: string;
  cycle?: string;
  cycle_label?: string;
  price?: string;
  students_limit?: number | string;
  staff_limit?: number | string;
  features?: string[];
  trial_days?: number;
}

export interface AgreementSection {
  heading: string;
  body: string;
}

export type AgreementStatus = "accepted" | "pending_payment" | "active" | "superseded" | "cancelled";

export interface Agreement {
  id: number;
  number: string;
  tenant: number;
  kind: "trial" | "subscription";
  kind_label: string;
  version: string;
  status: AgreementStatus;
  status_label: string;
  plan: number | null;
  plan_name: string | null;
  billing_cycle: string;
  amount: string | null;
  currency: string;
  institute_code: string;
  institute_legal_name: string;
  institute_address: string;
  signer_name: string;
  signer_designation: string;
  signer_cnic: string;
  signer_phone: string;
  signature: string;
  signed_at: string;
  ip_address: string;
  provider: AgreementProvider;
  schedule: AgreementSchedule;
  sections: AgreementSection[];
  payment_reference: string;
  payment_method: string | null;
  payment_paid_at: string | null;
  payment_reference_recorded: string | null;
  period_start: string | null;
  period_end: string | null;
  activated_at: string | null;
  payment_instructions?: string;
}

/** What the server would sign right now (preview before signing). */
export interface AgreementPreview {
  kind: "trial" | "subscription";
  version: string;
  provider: AgreementProvider;
  schedule: AgreementSchedule;
  sections: AgreementSection[];
  amount?: string | null;
  currency?: string;
  prefill?: Record<string, string>;
  renewal?: boolean;
  payment_instructions?: string;
}

export const AGREEMENT_TONE: Record<AgreementStatus, string> = {
  accepted: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  active: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  pending_payment: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  superseded: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  cancelled: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
};
