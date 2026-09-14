import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getCurrentUser, login as authLogin, signup as authSignup, logout as authLogout, type User } from "@/services/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (data: { email: string; password?: string }) => Promise<User>;
  signup: (data: { name: string; email: string; password?: string; mobile?: string }) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      const u = await getCurrentUser();
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();

    const handleUnauthorized = () => {
      setUser(null);
      setLoading(false);
    };

    window.addEventListener("manan:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("manan:unauthorized", handleUnauthorized);
    };
  }, []);

  const login = async (data: { email: string; password?: string }) => {
    const u = await authLogin(data);
    setUser(u);
    setLoading(false);
    return u;
  };

  const signup = async (data: { name: string; email: string; password?: string; mobile?: string }) => {
    const u = await authSignup(data);
    setUser(u);
    setLoading(false);
    return u;
  };

  const logout = async () => {
    try {
      await authLogout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
