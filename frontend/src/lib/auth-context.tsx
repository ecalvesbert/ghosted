"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { auth as authApi, type UserPublic } from "./api";

interface AuthState {
  token: string | null;
  user: UserPublic | null;
  loading: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  token: null,
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem("ghosted_token");
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback((newToken: string) => {
    localStorage.setItem("ghosted_token", newToken);
    setToken(newToken);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem("ghosted_token");
    if (stored) {
      setToken(stored);
      authApi.me(stored).then(setUser).catch(() => {
        localStorage.removeItem("ghosted_token");
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token && !user) {
      authApi.me(token).then(setUser).catch(() => logout());
    }
  }, [token, user, logout]);

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
