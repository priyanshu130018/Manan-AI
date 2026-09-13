import axios, { AxiosError, type AxiosInstance } from "axios";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8001/v1";

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL.replace(/\/+$/, ""),
  timeout: 120_000,
  withCredentials: false,
});

export function toFriendlyError(error: unknown): string {
  const err = error as AxiosError<{ detail?: string; message?: string; retry_after?: number }>;
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
  if (err?.request) return "Cannot reach the backend server. Make sure FastAPI is running on http://localhost:8001.";
  return err?.message || "Something went wrong.";
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const friendly = toFriendlyError(error);
    const retryAfter = error?.response?.data?.retry_after;
    return Promise.reject(Object.assign(error, { friendlyMessage: friendly, retryAfter }));
  },
);
