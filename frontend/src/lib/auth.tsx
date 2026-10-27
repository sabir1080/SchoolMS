"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, savedInstitute, tokens, type LoginResponse, type Subscription, type User } from "./api";

interface AuthState {
  user: User | null;
  subscription: Subscription | null;
  loading: boolean;
  login: (instituteCode: string, username: string, password: string) => Promise<User>;
  platformLogin: (username: string, password: string) => Promise<User>;
  /** Store tokens from a response that already logged the user in (e.g. registration). */
  acceptLogin: (data: LoginResponse) => Promise<User>;
  refreshSubscription: () => Promise<void>;
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

  useEffect(() => {
    if (!tokens.access) {
      setLoading(false);
      return;
    }
    api<User>("/api/auth/me/")
      .then(async (me) => {
        setUser(me);
        setSubscription(await fetchSubscription(me));
      })
      .catch(() => tokens.clear())
      .finally(() => setLoading(false));
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

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
    setSubscription(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, subscription, loading, login, platformLogin, acceptLogin, refreshSubscription, logout }}
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
