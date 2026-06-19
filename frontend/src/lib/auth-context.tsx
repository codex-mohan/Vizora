"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
  org_name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (data: {
    org_name: string;
    org_slug: string;
    email: string;
    password: string;
    full_name: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      const storedToken = localStorage.getItem("vizora_token");
      if (!storedToken) {
        if (!cancelled) setLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
        });
        if (!res.ok) throw new Error("Invalid token");
        const data = await res.json();
        if (!cancelled) {
          setToken(storedToken);
          setUser(data);
        }
      } catch {
        localStorage.removeItem("vizora_token");
        if (!cancelled) {
          setToken(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    hydrate();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Login failed");
    }
    const data = await res.json();
    localStorage.setItem("vizora_token", data.access_token);
    setToken(data.access_token);
    const userRes = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });
    if (userRes.ok) {
      setUser(await userRes.json());
    }
  }, []);

  const signup = useCallback(
    async (params: {
      org_name: string;
      org_slug: string;
      email: string;
      password: string;
      full_name: string;
    }) => {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed");
      }
      const data = await res.json();
      localStorage.setItem("vizora_token", data.access_token);
      setToken(data.access_token);
      const userRes = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (userRes.ok) {
        setUser(await userRes.json());
      }
    },
    [],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("vizora_token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, loading, login, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
