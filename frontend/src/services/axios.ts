import axios, { AxiosError, type AxiosInstance } from "axios";
import type { AppSettings } from "@/types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
if (!apiBaseUrl) {
  throw new Error("Missing required environment variable: VITE_API_BASE_URL");
}

export const API_BASE_URL: string = apiBaseUrl as string;

export interface ModelOption {
  value: string;
  label: string;
  provider: "gemini" | "ollama";
}

export const SETTINGS_KEY = "manan.settings";
export const DEFAULT_SETTINGS: AppSettings = {
  model: "gemini-3.6-flash",
  provider: "gemini",
  memoryEnabled: true,
};

export const MODEL_OPTIONS: ModelOption[] = [
  { value: "gemini-3.6-flash", label: "Gemini 3.6 Flash", provider: "gemini" },
  {
    value: "gpt-oss:120b",
    label: "GPT-OSS 120B (Ollama Cloud)",
    provider: "ollama",
  },
];

export function readSettings(): AppSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    let model = parsed.model;
    let opt = MODEL_OPTIONS.find((m) => m.value === model);
    if (!opt) {
      if (
        model &&
        (model.toLowerCase().includes("gpt") ||
          model.toLowerCase().includes("oss") ||
          model.toLowerCase().includes("gemma") ||
          model.toLowerCase().includes("qwen") ||
          model.toLowerCase().includes("llama") ||
          model.toLowerCase().includes("cloud"))
      ) {
        model = "gpt-oss:120b";
      } else {
        model = DEFAULT_SETTINGS.model;
      }
      opt = MODEL_OPTIONS.find((m) => m.value === model) || MODEL_OPTIONS[0];
    }
    const provider = opt.provider;
    return {
      model,
      provider,
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
  const err = error as AxiosError<{
    detail?: string;
    message?: string;
    retry_after?: number;
    error_code?: string;
  }>;
  if (err?.code === "ECONNABORTED") return "The request timed out. Please try again.";
  if (err?.response) {
    const data = err.response.data;
    const msg = data?.message || data?.detail;

    if (err.response.status === 429) {
      const retrySec = data?.retry_after ? Math.round(data.retry_after) : 30;
      return `AI rate limit reached. Please wait ${retrySec}s before trying again.`;
    }
    if (err.response.status === 404) {
      return msg || "API endpoint or resource not found.";
    }
    if (err.response.status === 401) {
      return msg || "Session expired. Please sign in again.";
    }
    if (err.response.status === 403) {
      return msg || "Access denied. You do not have permission for this resource.";
    }
    if (err.response.status === 422) {
      return msg || "Validation error in request data.";
    }
    if (err.response.status >= 500) {
      return msg || `Server error (${err.response.status}). Please try again later.`;
    }
    return msg || `Request failed with status ${err.response.status}.`;
  }
  if (err?.request)
    return `Cannot reach backend server at ${API_BASE_URL}. Ensure FastAPI is running.`;
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
        path === "/login" ||
        path === "/signup";
      if (!isAuthPage) {
        window.dispatchEvent(new CustomEvent("manan:unauthorized"));
        window.location.href = `/login?redirect=${encodeURIComponent(path)}`;
      }
    }
    const friendly = toFriendlyError(error);
    const retryAfter = error?.response?.data?.retry_after;
    return Promise.reject(Object.assign(error, { friendlyMessage: friendly, retryAfter }));
  },
);
