"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, tokens, type User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokens.access) {
      setLoading(false);
      return;
    }
    api<User>("/api/auth/me/")
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api<{ access: string; refresh: string; user: User }>(
      "/api/auth/login/",
      { method: "POST", body: JSON.stringify({ username, password }) },
      false,
    );
    tokens.set(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
