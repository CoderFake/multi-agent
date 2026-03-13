"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import * as authApi from "@/lib/auth";
import { api } from "@/lib/api-client";
import type { MeResponse } from "@/types/auth";
import type { ApiError } from "@/lib/api-client";

interface AuthContextValue {
  user: MeResponse | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Pages that don't require auth — no redirect on 401 */
const PUBLIC_PATHS = ["/login", "/change-password", "/accept-invite"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Check session on mount
  useEffect(() => {
    authApi
      .getMe()
      .then(setUser)
      .catch((e) => {
        setUser(null);
        const err = e as ApiError;
        // 401 on a protected page → redirect to login
        if (err.status_code === 401 && !PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
          router.replace("/login");
        }
      })
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      await authApi.login({ email, password });
      api.resetExpired();
      const me = await authApi.getMe();
      setUser(me);
      router.push("/dashboard");
    },
    [router]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore
    }
    setUser(null);
    router.push("/login");
  }, [router]);

  const refresh = useCallback(async () => {
    try {
      await authApi.refreshToken();
      const me = await authApi.getMe();
      setUser(me);
    } catch (e) {
      const err = e as ApiError;
      if (err.status_code === 401) {
        setUser(null);
        router.push("/login");
      }
    }
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
