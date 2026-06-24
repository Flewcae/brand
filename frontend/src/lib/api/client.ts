import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { tokenStorage } from "@/lib/auth/token-storage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

type RetryableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) return null;
  try {
    // SIMPLE_JWT.ROTATE_REFRESH_TOKENS is on -- every refresh call returns a
    // *new* refresh token too, the old one must be discarded.
    const response = await axios.post<{ access: string; refresh: string }>(
      `${API_BASE_URL}/auth/token/refresh/`,
      { refresh }
    );
    tokenStorage.set(response.data.access, response.data.refresh);
    return response.data.access;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableConfig | undefined;
    const isAuthEndpoint = originalRequest?.url?.includes("/auth/token");

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const newAccess = await refreshPromise;

      if (newAccess) {
        originalRequest.headers.set("Authorization", `Bearer ${newAccess}`);
        return apiClient(originalRequest);
      }

      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);
