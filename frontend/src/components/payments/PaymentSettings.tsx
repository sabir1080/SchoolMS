"use client";

import { useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, PasswordField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Account {
  provider: "jazzcash" | "easypaisa" | "safepay" | "stripe";
  label: string;
  is_enabled: boolean;
  test_mode: boolean;
  merchant_id: string;
  has_password: boolean;
  has_secret: boolean;
  is_ready: boolean;
  currency_ok: boolean;
}

interface Settings {
  currency_supported: boolean;
  accounts: Account[];
  currency: string;
  urls: { jazzcash_return: string; easypaisa_postback: string; easypaisa_ipn: string; stripe_webhook: string };
}

const TEXT = {
  jazzcash: { id: "Merchant ID", secret: "Integrity Salt", password: "Password" },
  easypaisa: { id: "Store ID", secret: "Hash Key (16 characters)", password: "" },
  safepay: { id: "API key", secret: "Secret key", password: "" },
  stripe: { id: "", secret: "Secret key (sk_live_… or sk_test_…)", password: "Webhook signing secret (whsec_…, recommended)" },
};

/** Institute settings: JazzCash and Easypaisa merchant accounts for online fee payments. */
export function PaymentSettings() {
  const { subscription } = useAuth();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<unknown>(null);
  const enabled = subscription?.plan.features.includes("online_payments");

  useEffect(() => {
    if (enabled) api<Settings>("/api/pay/settings/").then(setSettings).catch(setError);
  }, [enabled]);

  if (!enabled) {
    return (
      <Card>
        <h2 className="font-medium">Online fee payments</h2>
        <p className="mt-1 text-sm text-slate-500">Available on the Pro and Enterprise plans.</p>
      </Card>
    );
  }
  if (!settings) return <ErrorBox error={error} />;

  return (
    <Card>
      <h2 className="font-medium">Online fee payments</h2>
      <p className="mb-3 text-sm text-slate-500">
        Let parents pay bills with JazzCash, Easypaisa, Safepay (cards, wallets and bank accounts) or by card through Stripe.
        You need a merchant account with each one you use; they give you the details below. Keep &quot;Test mode&quot; on
        until the gateway tells you your account is live.
      </p>
      {!settings.currency_supported && (
        <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          JazzCash, Easypaisa and Safepay only accept PKR. Stripe can take {settings.currency}.
        </p>
      )}
      <div className="space-y-4">
        {settings.accounts.map((a) => (
          <AccountForm key={a.provider} account={a} urls={settings.urls} onSaved={setSettings} />
        ))}
      </div>
    </Card>
  );
}

function AccountForm({ account, urls, onSaved }: { account: Account; urls: Settings["urls"]; onSaved: (s: Settings) => void }) {
  const text = TEXT[account.provider];
  const [form, setForm] = useState({ merchant_id: account.merchant_id, password: "", secret: "", test_mode: account.test_mode, is_enabled: account.is_enabled });
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage("");
    try {
      const result = await api<Settings>("/api/pay/settings/", {
        method: "PATCH",
        body: JSON.stringify({ provider: account.provider, ...form }),
      });
      onSaved(result);
      setForm((f) => ({ ...f, password: "", secret: "" }));
      setMessage("Saved.");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form onSubmit={save} className="space-y-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">{account.label}</h3>
        <span className={`text-xs font-medium ${account.is_enabled ? "text-emerald-700" : "text-slate-500"}`}>
          {account.is_enabled ? (account.test_mode ? "On (test mode)" : "On") : "Off"}
        </span>
      </div>
      {!account.currency_ok && <p className="text-xs text-amber-700">Needs an institute that bills in PKR.</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {text.id && (
          <Field label={text.id} value={form.merchant_id} onChange={(e) => setForm({ ...form, merchant_id: e.target.value })} autoComplete="off" />
        )}
        {text.password && (
          <PasswordField
            label={text.password}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder={account.has_password ? "Saved — type to replace" : ""}
            autoComplete="new-password"
          />
        )}
        <PasswordField
          label={text.secret}
          value={form.secret}
          onChange={(e) => setForm({ ...form, secret: e.target.value })}
          placeholder={account.has_secret ? "Saved — type to replace" : ""}
          autoComplete="new-password"
        />
      </div>
      <div className="flex flex-wrap gap-4 text-sm">
        {account.provider === "stripe" ? (
          <span className="text-xs text-slate-500">Test or live follows your secret key (sk_test_ / sk_live_).</span>
        ) : (
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.test_mode} onChange={(e) => setForm({ ...form, test_mode: e.target.checked })} />
            Test mode (sandbox)
          </label>
        )}
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} />
          Show to parents
        </label>
      </div>
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer">Addresses to give {account.label}</summary>
        {account.provider === "jazzcash" && <p className="mt-1 break-all">Return URL: {urls.jazzcash_return}</p>}
        {account.provider === "easypaisa" && (
          <>
            <p className="mt-1 break-all">Postback URL: {urls.easypaisa_postback}</p>
            <p className="break-all">IPN URL (needed to confirm payments): {urls.easypaisa_ipn}</p>
          </>
        )}
        {account.provider === "safepay" && <p className="mt-1">Nothing to set: the return address is sent with each payment.</p>}
        {account.provider === "stripe" && (
          <p className="mt-1 break-all">
            Webhook endpoint (Stripe Dashboard → Developers → Webhooks, event checkout.session.completed): {urls.stripe_webhook}
          </p>
        )}
      </details>
      <ErrorBox error={error} />
      {message && <p className="text-sm text-emerald-700">{message}</p>}
      <Button type="submit">Save {account.label}</Button>
    </form>
  );
}
