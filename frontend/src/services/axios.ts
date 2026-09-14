import axios, { AxiosError, type AxiosInstance } from "axios";
import type { AppSettings } from "@/types";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

export const SETTINGS_KEY = "manan.settings";
export const DEFAULT_SETTINGS: AppSettings = {
  model: "gemini-3.6-flash",
  memoryEnabled: true,
};

export const MODEL_OPTIONS = [
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { value: "gemini-3.6-flash", label: "Gemini 3.6 Flash (Default)" },
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
  { value: "gemini-3-pro", label: "Gemini 3 Pro" },
  { value: "llama3.2", label: "Ollama (llama3.2)" },
];

export function readSettings(): AppSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      model: parsed.model || DEFAULT_SETTINGS.model,
      memoryEnabled: parsed.memoryEnabled ?? DEFAULT_SETTINGS.memoryEnabled,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function writeSettings(settings: AppSettings) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  window.dispatchEvent(new CustomEvent("manan:settings"));
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL.replace(/\/+$/, ""),
  timeout: 120_000,
  withCredentials: true,
});

export function toFriendlyError(error: unknown): string {
  const err = error as AxiosError<{ detail?: string; message?: string; retry_after?: number; error_code?: string }>;
  if (err?.code === "ECONNABORTED") return "The request timed out. Please try again.";
  if (err?.response) {
    if (err.response.status === 429) {
      const data = err.response.data;
      const retrySec = data?.retry_after ? Math.round(data.retry_after) : 30;
      return `AI rate limit reached. Please wait ${retrySec}s before trying again.`;
    }
    const data = err.response.data;
    return data?.detail || data?.message || `Request failed with status ${err.response.status}.`;
  }
  if (err?.request) return "Cannot reach the backend server. Make sure FastAPI is running on http://localhost:8000.";
  return err?.message || "Something went wrong.";
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && typeof window !== "undefined") {
      const path = window.location.pathname;
      const isAuthPage =
        path.endsWith("/login") ||
        path.endsWith("/signup") ||
        path === "/v2/login" ||
        path === "/v2/signup" ||
        path === "/login" ||
        path === "/signup";
      if (!isAuthPage) {
        window.dispatchEvent(new CustomEvent("manan:unauthorized"));
        window.location.href = `/v2/login?redirect=${encodeURIComponent(path)}`;
      }
    }
    const friendly = toFriendlyError(error);
    const retryAfter = error?.response?.data?.retry_after;
    return Promise.reject(Object.assign(error, { friendlyMessage: friendly, retryAfter }));
  },
);
