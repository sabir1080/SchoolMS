"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { applyBrand } from "./brand";
import { ApiError, SESSION_EXPIRED_EVENT, api, expiredNotice, savedInstitute, tokens, type LoginResponse, type Subscription, type User } from "./api";

interface AuthState {
  user: User | null;
  subscription: Subscription | null;
  loading: boolean;
  /** The server could not be reached while restoring the login (offline or waking up). */
  unreachable: boolean;
  retry: () => void;
  login: (instituteCode: string, username: string, password: string) => Promise<User>;
  platformLogin: (username: string, password: string) => Promise<User>;
  /** Store tokens from a response that already logged the user in (e.g. registration). */
  acceptLogin: (data: LoginResponse) => Promise<User>;
  refreshSubscription: () => Promise<void>;
  /** Reload the profile (e.g. after the institute's settings change). */
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

async function fetchSubscription(user: User | null) {
  if (!user?.tenant) return null;
  return api<Subscription>("/api/subscription/").catch(() => null);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [unreachable, setUnreachable] = useState(false);

  const restore = useCallback(() => {
    if (!tokens.access) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setUnreachable(false);
    api<User>("/api/auth/me/")
      .then(async (me) => {
        setUser(me);
        setSubscription(await fetchSubscription(me));
      })
      .catch((err) => {
        // Only a real "not logged in" ends the login; no connection keeps it for a retry.
        if (err instanceof ApiError && err.status === 0) setUnreachable(true);
        else tokens.clear();
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(restore, [restore]);

  // The saved login ran out (or was refused) while the app was open: back to the login page with a notice.
  useEffect(() => {
    const onExpired = () => {
      setUser((current) => {
        expiredNotice.set(current?.role ?? "user");
        return null;
      });
      setSubscription(null);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  const acceptLogin = useCallback(async (data: LoginResponse) => {
    tokens.set(data.access, data.refresh);
    if (data.user.tenant) savedInstitute.set({ name: data.user.tenant.name, slug: data.user.tenant.slug });
    setSubscription(await fetchSubscription(data.user));
    setUser(data.user);
    return data.user;
  }, []);

  const login = useCallback(
    async (instituteCode: string, username: string, password: string) => {
      const data = await api<LoginResponse>(
        "/api/auth/login/",
        { method: "POST", body: JSON.stringify({ institute_code: instituteCode, username, password }) },
        false,
      );
      return acceptLogin(data);
    },
    [acceptLogin],
  );

  const platformLogin = useCallback(
    async (username: string, password: string) => {
      const data = await api<LoginResponse>(
        "/api/auth/platform-login/",
        { method: "POST", body: JSON.stringify({ username, password }) },
        false,
      );
      return acceptLogin(data);
    },
    [acceptLogin],
  );

  const refreshSubscription = useCallback(async () => {
    setSubscription(await fetchSubscription(user));
  }, [user]);

  const refreshUser = useCallback(async () => {
    setUser(await api<User>("/api/auth/me/"));
  }, []);

  // Use the institute's theme colour while signed in.
  useEffect(() => {
    if (user) applyBrand(user.tenant?.brand?.hex);
  }, [user]);

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
    setSubscription(null);
    applyBrand(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        subscription,
        loading,
        unreachable,
        retry: restore,
        login,
        platformLogin,
        acceptLogin,
        refreshSubscription,
        refreshUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
