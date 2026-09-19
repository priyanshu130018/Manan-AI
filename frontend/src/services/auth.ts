import { api, API_BASE_URL } from "./axios";
import type { ApiResponse } from "@/types";

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
    const res = await api.get<ApiResponse<User>>("/auth/me");
    return res.data?.data || null;
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
  const res = await api.post<ApiResponse<User>>("/auth/signup", data);
  const user = res.data?.data;
  if (!user) throw new Error("No user profile returned from signup.");
  return user;
}

export async function login(data: {
  email: string;
  password?: string;
}): Promise<User> {
  const res = await api.post<ApiResponse<User>>("/auth/login", data);
  const user = res.data?.data;
  if (!user) throw new Error("No user profile returned from login.");
  return user;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function updateProfile(data: {
  name?: string;
  mobile?: string;
}): Promise<User> {
  const res = await api.patch<ApiResponse<User>>("/profile", data);
  if (!res.data?.data) throw new Error("Failed to update profile.");
  return res.data.data;
}

export async function changePassword(data: {
  current_password?: string;
  new_password?: string;
}): Promise<void> {
  await api.post("/profile/password", data);
}

export function getGoogleAuthUrl(): string {
  const base = API_BASE_URL.replace(/\/+$/, "");
  return `${base}/auth/google/login`;
}
