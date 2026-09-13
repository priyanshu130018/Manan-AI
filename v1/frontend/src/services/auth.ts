import { api } from "./axios";

export interface User {
  id: string;
  name: string;
  email: string;
  mobile?: string | null;
  auth_provider: "local" | "google";
  created_at?: number;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user: User;
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    const res = await api.get<{ success: boolean; user: User }>("/auth/me");
    return res.data?.user || null;
  } catch {
    return null;
  }
}

export async function signup(data: {
  name: string;
  email: string;
  password?: string;
  mobile?: string;
}): Promise<User> {
  const res = await api.post<AuthResponse>("/auth/signup", data);
  return res.data.user;
}

export async function login(data: {
  email: string;
  password?: string;
}): Promise<User> {
  const res = await api.post<AuthResponse>("/auth/login", data);
  return res.data.user;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getGoogleAuthUrl(): Promise<string> {
  const res = await api.get<{ auth_url: string }>("/auth/google/url");
  return res.data.auth_url;
}

export async function updateProfile(data: {
  name?: string;
  mobile?: string;
}): Promise<User> {
  const res = await api.patch<{ success: boolean; user: User }>("/profile", data);
  return res.data.user;
}

export async function changePassword(data: {
  current_password?: string;
  new_password?: string;
}): Promise<void> {
  await api.post("/profile/password", data);
}
