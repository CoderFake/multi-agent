/**
 * Auth API helpers — typed wrappers around api client.
 */
import { api } from "./api-client";
import type { MeResponse, LoginRequest } from "@/types/auth";

export async function login(data: LoginRequest): Promise<{ message: string; user_id: string }> {
  return api.post("/auth/login", data);
}

export async function logout(): Promise<{ message: string }> {
  return api.post("/auth/logout");
}

export async function refreshToken(): Promise<{ message: string }> {
  return api.post("/auth/refresh");
}

export async function getMe(): Promise<MeResponse> {
  return api.get("/auth/me");
}
