/**
 * Permissions API functions.
 */
import { api } from "@/lib/api-client";
import type { UIPermissions } from "@/types/models";

export function fetchUIPermissions() {
  return api.get<UIPermissions>("/permissions/me");
}
