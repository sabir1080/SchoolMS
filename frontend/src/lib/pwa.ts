"use client";

import { useEffect, useState } from "react";

import { api } from "./api";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferredPrompt: InstallPromptEvent | null = null;
const listeners = new Set<() => void>();

/** Register the service worker once (installable app, offline page, notifications). */
export function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event as InstallPromptEvent;
    listeners.forEach((fn) => fn());
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    listeners.forEach((fn) => fn());
  });
  navigator.serviceWorker.register("/sw.js").catch(() => undefined);
}

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function isIos() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

/** Whether the "Install app" button should show, and what tapping it does. */
export function useInstallApp() {
  const [state, setState] = useState<"hidden" | "prompt" | "ios">("hidden");

  useEffect(() => {
    const update = () => {
      if (isStandalone()) setState("hidden");
      else if (deferredPrompt) setState("prompt");
      else if (isIos()) setState("ios");
      else setState("hidden");
    };
    update();
    listeners.add(update);
    return () => {
      listeners.delete(update);
    };
  }, []);

  async function install() {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice.catch(() => undefined);
    deferredPrompt = null;
    listeners.forEach((fn) => fn());
  }

  return { state, install };
}

export interface PushInfo {
  enabled: boolean;
  public_key: string;
  devices: number;
}

export function pushSupported() {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

function keyBytes(base64url: string) {
  const padded = (base64url + "=".repeat((4 - (base64url.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

/** This device's push subscription, if notifications are on here. */
export async function currentSubscription() {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
}

/** Ask for permission, subscribe this device and tell the server. */
export async function turnOnNotifications(publicKey: string) {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Notifications are blocked. Allow them for this site in your browser settings.");
  const registration = await navigator.serviceWorker.ready;
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(publicKey) }));
  return api<{ devices: number }>("/api/push/", { method: "POST", body: JSON.stringify(subscription.toJSON()) });
}

export async function turnOffNotifications() {
  const subscription = await currentSubscription();
  if (!subscription) return;
  await api("/api/push/", { method: "POST", body: JSON.stringify({ action: "unsubscribe", endpoint: subscription.endpoint }) });
  await subscription.unsubscribe();
}
