"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getMyAgency, login as loginRequest, register as registerRequest } from "@/lib/api/auth";
import type { Agency } from "@/lib/api/types";
import { tokenStorage } from "@/lib/auth/token-storage";

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  agency: Agency | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, agencyName: string) => Promise<void>;
  logout: () => void;
  refreshAgency: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // No token means nothing to load -- start "not loading" rather than
  // flipping it off inside the effect (avoids a synchronous setState-in-effect).
  const [isLoading, setIsLoading] = useState(() => Boolean(tokenStorage.getAccess()));
  const [agency, setAgency] = useState<Agency | null>(null);

  const loadAgency = useCallback(async () => {
    try {
      const data = await getMyAgency();
      setAgency(data);
      setIsAuthenticated(true);
    } catch {
      setAgency(null);
      setIsAuthenticated(false);
    }
  }, []);

  useEffect(() => {
    if (!tokenStorage.getAccess()) {
      return;
    }
    let isCurrent = true;
    async function run() {
      await loadAgency();
      if (isCurrent) setIsLoading(false);
    }
    void run();
    return () => {
      isCurrent = false;
    };
  }, [loadAgency]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access, refresh } = await loginRequest({ email, password });
      tokenStorage.set(access, refresh);
      await loadAgency();
    },
    [loadAgency]
  );

  const register = useCallback(
    async (email: string, password: string, agencyName: string) => {
      await registerRequest({ email, password, agency_name: agencyName });
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    tokenStorage.clear();
    setAgency(null);
    setIsAuthenticated(false);
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      isLoading,
      agency,
      login,
      register,
      logout,
      refreshAgency: loadAgency,
    }),
    [isAuthenticated, isLoading, agency, login, register, logout, loadAgency]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
