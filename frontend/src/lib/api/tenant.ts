/**
 * Tenant API functions — org-scoped: users, groups, permissions, audit logs, agents.
 * All calls use X-Org-Id header (auto-attached by api-client).
 */
import { api } from "@/lib/api-client";
import type {
    TenantUser,
    TenantUserUpdate,
    Group,
    GroupCreate,
    GroupUpdate,
    Permission,
    AuditLog,
    Agent,
} from "@/types/models";
import type { PaginatedResponse } from "@/types/api";

// ============================================================================
// Users
// ============================================================================

export function fetchTenantUsers(params: {
    page?: number;
    pageSize?: number;
    search?: string;
}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    if (params.search) q.set("search", params.search);
    return api.get<PaginatedResponse<TenantUser>>(`/tenant/users?${q}`);
}

export function fetchTenantUser(userId: string) {
    return api.get<TenantUser>(`/tenant/users/${userId}`);
}

export function updateTenantUser(userId: string, data: TenantUserUpdate) {
    return api.put<TenantUser>(`/tenant/users/${userId}`, data);
}

export function removeTenantUser(userId: string) {
    return api.delete(`/tenant/users/${userId}`);
}

// ============================================================================
// Groups
// ============================================================================

export function fetchTenantGroups() {
    return api.get<PaginatedResponse<Group>>("/tenant/groups");
}

export function createTenantGroup(data: GroupCreate) {
    return api.post<Group>("/tenant/groups", data);
}

export function updateTenantGroup(groupId: string, data: GroupUpdate) {
    return api.put<Group>(`/tenant/groups/${groupId}`, data);
}

export function deleteTenantGroup(groupId: string) {
    return api.delete(`/tenant/groups/${groupId}`);
}

// ── Group Permissions ──

export function fetchGroupPermissions(groupId: string) {
    return api.get<Permission[]>(`/tenant/groups/${groupId}/permissions`);
}

export function assignGroupPermissions(groupId: string, permissionIds: string[]) {
    return api.post(`/tenant/groups/${groupId}/permissions`, { permission_ids: permissionIds });
}

export function revokeGroupPermissions(groupId: string, permissionIds: string[]) {
    return api.delete(`/tenant/groups/${groupId}/permissions`, { permission_ids: permissionIds });
}

// ── Group Members ──

export function fetchGroupMembers(groupId: string) {
    return api.get<TenantUser[]>(`/tenant/groups/${groupId}/members`);
}

export function addGroupMember(groupId: string, userIds: string[]) {
    return api.post(`/tenant/groups/${groupId}/members`, { user_ids: userIds });
}

export function removeGroupMember(groupId: string, userId: string) {
    return api.delete(`/tenant/groups/${groupId}/members/${userId}`);
}

// ============================================================================
// Permissions
// ============================================================================

export function fetchTenantPermissions() {
    return api.get<Permission[]>("/tenant/permissions");
}

// ============================================================================
// Audit Logs
// ============================================================================

export function fetchTenantAuditLogs(params: {
    page?: number;
    pageSize?: number;
    action?: string;
    resourceType?: string;
    userId?: string;
}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    if (params.action) q.set("action", params.action);
    if (params.resourceType) q.set("resource_type", params.resourceType);
    if (params.userId) q.set("user_id", params.userId);
    return api.get<PaginatedResponse<AuditLog>>(`/tenant/audit-logs?${q}`);
}

// ============================================================================
// Agents
// ============================================================================

export function fetchTenantAgents() {
    return api.get<Agent[]>("/tenant/agents");
}
