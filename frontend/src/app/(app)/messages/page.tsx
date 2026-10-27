"use client";

import { useCallback, useEffect, useState } from "react";

import type { AcademicSession, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";

interface Message {
  id: number;
  student_name: string | null;
  recipient: string;
  phone: string;
  body: string;
  kind: string;
  kind_label: string;
  status: "pending" | "sent" | "failed";
  error: string;
  created_at: string;
  whatsapp_link: string | null;
}

interface Outbox {
  count: number;
  results: Message[];
  summary: Record<Message["status"], number>;
  automatic: boolean;
}

interface Settings {
  channel: string;
  channels: { value: string; label: string }[];
  twilio_account_sid: string;
  twilio_from: string;
  has_token: boolean;
  is_automatic: boolean;
  absent_alerts: boolean;
  result_alerts: boolean;
  homework_alerts: boolean;
}

const FILTERS: [Message["status"], string][] = [
  ["pending", "To send"],
  ["failed", "Failed"],
  ["sent", "Sent"],
];
const TONE: Record<Message["status"], string> = {
  pending: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  sent: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  failed: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export default function MessagesPage() {
  const [status, setStatus] = useState<Message["status"]>("pending");
  const [outbox, setOutbox] = useState<Outbox | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");

  const load = useCallback(() => {
    let current = true;
    api<Outbox>(`/api/messages/?status=${status}&page_size=100`)
      .then((d) => current && setOutbox(d))
      .catch((e) => current && setError(e));
    return () => {
      current = false;
    };
  }, [status]);
  useEffect(load, [load]);

  async function act(path: string, body?: object, done?: (r: Record<string, number>) => string) {
    setError(null);
    setNotice("");
    try {
      const result = await api<Record<string, number>>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      if (done) setNotice(done(result));
      load();
    } catch (err) {
      setError(err);
    }
  }

  async function openWhatsApp(m: Message) {
    window.open(m.whatsapp_link!, "_blank", "noopener");
    await act(`/api/messages/${m.id}/mark-sent/`);
  }

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold">Messages to parents</h1>
      <p className="text-sm text-slate-500">
        Absent alerts, results and homework are added here automatically (you choose which in the settings below). Fee reminders and notices are sent
        when you ask.
      </p>
      <Actions onAct={act} automatic={outbox?.automatic ?? false} pending={(outbox?.summary.pending ?? 0) + (outbox?.summary.failed ?? 0)} />
      <ErrorBox error={error} />
      {notice && <p className="text-sm text-emerald-700">{notice}</p>}

      <div className="flex w-max gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800" role="tablist">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={status === key}
            onClick={() => setStatus(key)}
            className={`rounded-lg px-3 py-2 text-sm ${status === key ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"}`}
          >
            {label} {outbox && <span className="text-xs text-slate-500">({outbox.summary[key]})</span>}
          </button>
        ))}
      </div>

      <Card>
        {!outbox ? null : outbox.results.length === 0 ? (
          <p className="text-sm text-slate-500">No messages here.</p>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-800">
            {outbox.results.map((m) => (
              <li key={m.id} className="py-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium">{m.recipient || m.student_name}</span>
                  {m.student_name && m.recipient !== m.student_name && <span className="text-xs text-slate-500">for {m.student_name}</span>}
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] dark:bg-slate-800">{m.kind_label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] ${TONE[m.status]}`}>{m.status === "pending" ? "To send" : m.status === "sent" ? "Sent" : "Failed"}</span>
                  <span className="ml-auto text-xs text-slate-500">{new Date(m.created_at).toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}</span>
                </div>
                <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{m.body}</p>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs">
                  <span className="text-slate-500">{m.phone || "No phone"}</span>
                  {m.error && <span className="text-red-600">{m.error}</span>}
                  {m.status !== "sent" && m.whatsapp_link && (
                    <button onClick={() => openWhatsApp(m)} className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white">
                      Send on WhatsApp
                    </button>
                  )}
                  {m.status !== "sent" && (
                    <button onClick={() => api(`/api/messages/${m.id}/`, { method: "DELETE" }).then(load).catch(setError)} className="text-slate-500 hover:underline">
                      Remove
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <MessageSettings onSaved={load} />
    </div>
  );
}

function Actions({ onAct, automatic, pending }: { onAct: (p: string, b?: object, d?: (r: Record<string, number>) => string) => void; automatic: boolean; pending: number }) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const current = sessions.items.find((s) => s.is_current);
  const sections = useList<Section>(current ? `/api/academics/sections/?session=${current.id}` : null);
  const [text, setText] = useState("");
  const [section, setSection] = useState("");
  const [writing, setWriting] = useState(false);

  return (
    <Card>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onAct("/api/messages/fee-reminders/", undefined, (r) => (r.created ? `${r.created} fee reminder(s) added.` : "No overdue fees, or reminders were already made today."))}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700"
        >
          Send fee reminders
        </button>
        <button onClick={() => setWriting(!writing)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700">
          {writing ? "Close notice" : "Write a notice"}
        </button>
        {automatic && pending > 0 && (
          <button
            onClick={() => onAct("/api/messages/send-pending/", undefined, (r) => `${r.sent} sent, ${r.failed} failed${r.left ? `, ${r.left} left — press again` : ""}.`)}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white"
          >
            Send all waiting ({pending})
          </button>
        )}
      </div>
      {writing && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onAct("/api/messages/notice/", { text, section: section ? Number(section) : null }, (r) => `Notice added for ${r.created} parent(s).`);
            setText("");
            setWriting(false);
          }}
          className="mt-3 space-y-3"
        >
          <label className="block space-y-1">
            <span className="text-sm font-medium">Notice</span>
            <textarea
              required
              maxLength={600}
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="e.g. School will remain closed tomorrow due to rain."
              className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
            />
          </label>
          <div className="max-w-xs">
            <SelectField
              label="To"
              value={section}
              onChange={(e) => setSection(e.target.value)}
              options={[["", "All parents"], ...sections.items.map((s) => [String(s.id), `${terms.section}: ${s.program_name} - ${s.name}`] as [string, string])]}
            />
          </div>
          <Button type="submit">Add notice</Button>
        </form>
      )}
    </Card>
  );
}

function MessageSettings({ onSaved }: { onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [token, setToken] = useState("");
  const [testPhone, setTestPhone] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (open && !settings) api<Settings>("/api/messages/settings/").then(setSettings).catch(setError);
  }, [open, settings]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage("");
    try {
      const s = settings!;
      const body = {
        channel: s.channel,
        twilio_account_sid: s.twilio_account_sid,
        twilio_auth_token: token,
        twilio_from: s.twilio_from,
        absent_alerts: s.absent_alerts,
        result_alerts: s.result_alerts,
        homework_alerts: s.homework_alerts,
      };
      setSettings(await api<Settings>("/api/messages/settings/", { method: "PATCH", body: JSON.stringify(body) }));
      setToken("");
      setMessage("Settings saved.");
      onSaved();
    } catch (err) {
      setError(err);
    }
  }

  async function test() {
    setError(null);
    setMessage("");
    try {
      await api("/api/messages/test/", { method: "POST", body: JSON.stringify({ phone: testPhone }) });
      setMessage("Test message sent.");
    } catch (err) {
      setError(err);
    }
  }

  const twilio = settings?.channel.startsWith("twilio");
  return (
    <Card>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between text-left">
        <h2 className="font-medium">Message settings</h2>
        <span className="text-sm text-indigo-600">{open ? "Close" : "Open"}</span>
      </button>
      {open && settings && (
        <form onSubmit={save} className="mt-4 space-y-4">
          <fieldset className="space-y-2">
            <legend className="mb-1 text-sm font-medium">How to send</legend>
            {settings.channels.map((c) => (
              <label key={c.value} className="flex items-center gap-2 text-sm">
                <input type="radio" name="channel" checked={settings.channel === c.value} onChange={() => setSettings({ ...settings, channel: c.value })} />
                {c.label}
              </label>
            ))}
            <p className="text-xs text-slate-500">
              WhatsApp (free): each message gets a “Send on WhatsApp” button that opens WhatsApp on your phone with the text ready. Twilio sends by itself
              (paid account at twilio.com; WhatsApp needs approved message templates).
            </p>
          </fieldset>
          {twilio && (
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Twilio Account SID" value={settings.twilio_account_sid} onChange={(e) => setSettings({ ...settings, twilio_account_sid: e.target.value })} />
              <Field label="Auth Token" type="password" value={token} placeholder={settings.has_token ? "Saved — leave empty to keep" : ""} onChange={(e) => setToken(e.target.value)} autoComplete="off" />
              <Field label="Sender number" placeholder="+14155238886" value={settings.twilio_from} onChange={(e) => setSettings({ ...settings, twilio_from: e.target.value })} />
            </div>
          )}
          <fieldset className="space-y-2">
            <legend className="mb-1 text-sm font-medium">Automatic alerts</legend>
            {(
              [
                ["absent_alerts", "Tell parents when their child is marked absent (same day)"],
                ["result_alerts", "Send each student's result when an exam result is published"],
                ["homework_alerts", "Send the homework to parents when a teacher adds it"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={settings[key]} onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })} />
                {label}
              </label>
            ))}
          </fieldset>
          <ErrorBox error={error} />
          {message && <p className="text-sm text-emerald-700">{message}</p>}
          <Button type="submit">Save settings</Button>
          {settings.is_automatic && (
            <div className="flex flex-wrap items-end gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
              <div className="w-48">
                <Field label="Test number" placeholder="0300-1234567" value={testPhone} onChange={(e) => setTestPhone(e.target.value)} />
              </div>
              <button type="button" onClick={test} className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700">
                Send test message
              </button>
            </div>
          )}
        </form>
      )}
    </Card>
  );
}
