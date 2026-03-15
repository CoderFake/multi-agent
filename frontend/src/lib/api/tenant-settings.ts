/**
 * Tenant Settings API — org settings (name, timezone, logo).
 * All calls use X-Org-Id header (auto-attached by api-client).
 */
import { api } from "@/lib/api-client";
import type { Organization, TimezoneOption, TenantOrgUpdateData } from "@/types/models";


export function fetchOrgSettings() {
    return api.get<Organization>("/tenant/settings");
}

export function updateOrgSettings(data: TenantOrgUpdateData) {
    return api.patch<Organization>("/tenant/settings", data);
}

export function uploadOrgLogo(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return api.postForm<{ logo_url: string }>("/tenant/settings/logo", formData);
}

export function fetchTimezones() {
    return api.get<TimezoneOption[]>("/tenant/settings/timezones");
}
