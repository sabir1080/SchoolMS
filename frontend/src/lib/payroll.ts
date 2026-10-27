export interface Employee {
  id: number;
  name: string;
  designation: string;
  phone: string;
  cnic: string;
  join_date: string | null;
  basic_salary: string;
  allowance: string;
  bank_account: string;
  user: number | null;
  user_name: string | null;
  is_active: boolean;
}

export interface Payslip {
  id: number;
  employee: number;
  employee_name: string;
  designation: string;
  bank_account: string;
  period: string;
  basic: string;
  allowance: string;
  bonus: string;
  deduction: string;
  note: string;
  gross: string;
  net: string;
  status: "unpaid" | "paid";
  paid_on: string | null;
  method: string;
  method_label: string;
  reference: string;
}

/** "2026-10" -> "October 2026". */
export function monthName(period: string) {
  const [y, m] = period.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}
