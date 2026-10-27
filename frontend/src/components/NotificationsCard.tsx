"use client";

import { useEffect, useState } from "react";

import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { currentSubscription, pushSupported, turnOffNotifications, turnOnNotifications, type PushInfo } from "@/lib/pwa";

/** Turn phone notifications (absent alerts, fees, results, homework) on or off for this device. */
export function NotificationsCard({ compact = false }: { compact?: boolean }) {
  const [info, setInfo] = useState<PushInfo | null>(null);
  const [on, setOn] = useState<boolean | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!pushSupported()) return;
    api<PushInfo>("/api/push/")
      .then(setInfo)
      .catch(() => setInfo(null));
    currentSubscription()
      .then((s) => setOn(Boolean(s)))
      .catch(() => setOn(false));
  }, []);

  if (!info?.enabled || on === null) return null;
  // On the dashboard the card only invites turning notifications on (it stays to confirm it worked).
  if (compact && on && !message) return null;

  async function run(action: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      await action();
      setMessage(done);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2 className="font-medium">Phone notifications</h2>
      <p className="mt-1 text-sm text-slate-500">
        {on
          ? "On for this device. You will get alerts like absence, fees, results and homework here."
          : "Get alerts like absence, fees, results and homework on this phone, free."}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {on ? (
          <>
            <Button
              type="button"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  const res = await api<{ sent: number }>("/api/push/", { method: "POST", body: JSON.stringify({ action: "test" }) });
                  if (!res.sent) throw new Error("The test notification could not be sent. Please try again.");
                }, "Test notification sent.")
              }
            >
              Send a test
            </Button>
            <button
              type="button"
              disabled={busy}
              onClick={() => run(() => turnOffNotifications().then(() => setOn(false)), "Notifications turned off on this device.")}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
            >
              Turn off
            </button>
          </>
        ) : (
          <Button
            type="button"
            disabled={busy}
            onClick={() => run(() => turnOnNotifications(info.public_key).then(() => setOn(true)), "Notifications are on.")}
          >
            Turn on notifications
          </Button>
        )}
      </div>
      <ErrorBox error={error} />
      {message && <p className="mt-2 text-sm text-emerald-700">{message}</p>}
    </Card>
  );
}
