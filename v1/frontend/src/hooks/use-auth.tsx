import React, { createContext, useContext, type ReactNode } from "react";

export interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: () => Promise<void>;
  signup: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const anonymousUser: User = {
  id: "anonymous",
  name: "Guest",
  email: "",
};

const AuthContext = createContext<AuthContextType>({
  user: anonymousUser,
  loading: false,
  login: async () => {},
  signup: async () => {},
  logout: async () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <AuthContext.Provider
      value={{
        user: anonymousUser,
        loading: false,
        login: async () => {},
        signup: async () => {},
        logout: async () => {},
        refreshUser: async () => {},
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}
