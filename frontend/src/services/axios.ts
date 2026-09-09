import axios, { AxiosError, type AxiosInstance } from "axios";
import type { AppSettings } from "@/types";

export const SETTINGS_KEY = "manan.settings";
export const DEFAULT_SETTINGS: AppSettings = {
  backendUrl: "http://localhost:8000",
  modelName: "gemini-2.5-flash",
};

export function readSettings(): AppSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<AppSettings>) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function writeSettings(settings: AppSettings) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  window.dispatchEvent(new CustomEvent("manan:settings"));
}

export const api: AxiosInstance = axios.create({ timeout: 120_000 });

api.interceptors.request.use((config) => {
  const { backendUrl, modelName } = readSettings();
  config.baseURL = backendUrl.replace(/\/+$/, "");
  config.headers.set("X-Model-Name", modelName);
  return config;
});

export function toFriendlyError(error: unknown): string {
  const err = error as AxiosError<{ detail?: string; message?: string }>;
  if (err?.code === "ECONNABORTED") return "The request timed out. Please try again.";
  if (err?.response) {
    const data = err.response.data;
    return data?.detail || data?.message || `Request failed with status ${err.response.status}.`;
  }
  if (err?.request) return "Cannot reach the backend. Check the Backend URL in Settings.";
  return err?.message || "Something went wrong.";
}

api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(Object.assign(error, { friendlyMessage: toFriendlyError(error) })),
);
