import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRedirecting = false;

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (
      err.response?.status === 401 &&
      typeof window !== "undefined" &&
      !isRedirecting
    ) {
      isRedirecting = true;
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  error?: { code: string; message: string };
};

export function extractApiError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const detail = e.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (typeof detail === "object" && detail !== null) return JSON.stringify(detail);
    const msg = e.response?.data?.error?.message;
    if (msg) return msg;
    return e.response ? `Server error ${e.response.status}` : "Network error — is the server running?";
  }
  return e instanceof Error ? e.message : "Unknown error";
}
