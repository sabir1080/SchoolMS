import { api } from "./api";

export interface PayOption {
  provider: "jazzcash" | "easypaisa" | "demo";
  label: string;
  test_mode: boolean;
}

export interface OnlinePayment {
  reference: string;
  provider: string;
  provider_label: string;
  amount: string;
  status: "pending" | "success" | "failed";
  message: string;
  invoice: number;
  invoice_title: string;
  student: string;
  test_mode: boolean;
  created_at: string;
}

interface StartResponse {
  payment: OnlinePayment;
  redirect?: string;
  method?: "POST";
  action?: string;
  fields?: Record<string, string>;
}

/** Start an online payment and send the browser to the gateway (or the demo page). */
export async function startPayment(invoice: number, provider: string, go: (path: string) => void) {
  const res = await api<StartResponse>("/api/pay/start/", {
    method: "POST",
    body: JSON.stringify({ invoice, provider }),
  });
  if (res.redirect) {
    go(res.redirect);
    return;
  }
  // The gateways expect a normal form POST from the customer's browser.
  const form = document.createElement("form");
  form.method = "POST";
  form.action = res.action!;
  for (const [name, value] of Object.entries(res.fields ?? {})) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}
