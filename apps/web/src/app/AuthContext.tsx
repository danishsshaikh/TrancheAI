import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";
import { currentUser, login as apiLogin } from "../api/client";
import type { User } from "../api/client";

const STORAGE_KEY = "trancheai.auth";

interface AuthState {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    currentUser(token).then(setUser).catch(() => {
      localStorage.removeItem(STORAGE_KEY);
      setToken(null);
    });
  }, [token]);

  const value = useMemo<AuthState>(() => ({
    token,
    user,
    login: async (email: string, password: string) => {
      const session = await apiLogin(email, password);
      localStorage.setItem(STORAGE_KEY, session.accessToken);
      setToken(session.accessToken);
      setUser(session.user);
    },
    logout: () => {
      localStorage.removeItem(STORAGE_KEY);
      setToken(null);
      setUser(null);
    },
  }), [token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}

export function useToken() {
  const { token } = useAuth();
  if (!token) throw new Error("Authentication required");
  return token;
}
