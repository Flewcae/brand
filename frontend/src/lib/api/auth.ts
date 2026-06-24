import { apiClient } from "@/lib/api/client";
import type { Agency, User } from "@/lib/api/types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  agency_name: string;
}

export async function login(payload: LoginPayload) {
  const { data } = await apiClient.post<{ access: string; refresh: string }>(
    "/auth/token/",
    payload
  );
  return data;
}

export async function register(payload: RegisterPayload) {
  const { data } = await apiClient.post<{ user: User; agency: Agency }>(
    "/auth/register/",
    payload
  );
  return data;
}

export async function getMyAgency() {
  const { data } = await apiClient.get<Agency>("/agencies/me/");
  return data;
}
