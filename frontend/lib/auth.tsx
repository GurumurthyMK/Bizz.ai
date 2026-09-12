"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  type AuthCredentials,
} from "@/lib/api";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  /** True once the initial session check has finished. */
  isReady: boolean;
  login: (credentials: AuthCredentials) => Promise<void>;
  register: (credentials: AuthCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = React.useState<User | null>(null);
  const [isReady, setIsReady] = React.useState(false);

  const refresh = React.useCallback(async () => {
    try {
      setUser(await getCurrentUser());
    } catch (error) {
      // Only 401 means "no session". Anything else also yields signed-out
      // state here; pages surface fetch errors through their own states.
      if (!(error instanceof ApiError) || error.status !== 401) {
        // eslint-disable-next-line no-console
        console.error("Session check failed", error);
      }
      setUser(null);
    } finally {
      setIsReady(true);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = React.useCallback(
    async (credentials: AuthCredentials) => {
      const session = await loginUser(credentials);
      setUser(session.user);
      router.push("/overview");
      router.refresh();
    },
    [router]
  );

  const register = React.useCallback(
    async (credentials: AuthCredentials) => {
      const session = await registerUser(credentials);
      setUser(session.user);
      router.push("/overview");
      router.refresh();
    },
    [router]
  );

  const logout = React.useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
      router.push("/login");
      router.refresh();
    }
  }, [router]);

  const value = React.useMemo(
    () => ({ user, isLoading: !isReady, isReady, login, register, logout, refresh }),
    [user, isReady, login, register, logout, refresh]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (context == null) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

export { AuthProvider, useAuth };
