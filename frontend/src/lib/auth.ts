/**
 * Auth API helpers — typed wrappers around api client.
 */
import { api } from "./api-client";
import type { MeResponse, LoginRequest } from "@/types/auth";

export async function login(data: LoginRequest): Promise<{
  message: string;
  user_id: string;
  must_change_password: boolean;
}> {
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

export async function uploadAvatar(file: File): Promise<{ avatar_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return api.postForm("/auth/avatar", formData);
}

export async function confirmInvite(token: string): Promise<{ email: string; message: string }> {
  return api.post("/invites/confirm", { token });
}

export async function changePassword(data: {
  current_password: string;
  new_password: string;
}): Promise<{ message: string }> {
  return api.post("/auth/change-password", data);
}
