/**
 * System API functions — organization, agent, provider, MCP server, settings.
 * Pages/hooks call these, NOT api.get/post directly.
 */
import { api } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type {
  OrganizationListItem,
  Organization,
  OrgCreateData,
  OrgUpdateData,
  OrgMember,
  AddMemberData,
  SystemAgent,
  AgentCreateData,
  AgentUpdateData,
  SystemProvider,
  ProviderUpdateData,
  SystemMcpServer,
  McpServerCreateData,
  McpServerUpdateData,
  SystemSetting,
  SettingUpdateData,
} from "@/types/models";

// ============================================================================
// Organizations
// ============================================================================

export function fetchOrganizations(params: {
  page: number;
  pageSize: number;
  search?: string;
}) {
  const searchParam = params.search
    ? `&search=${encodeURIComponent(params.search)}`
    : "";
  return api.get<PaginatedResponse<OrganizationListItem>>(
    `/system/organizations?page=${params.page}&page_size=${params.pageSize}${searchParam}`,
  );
}

export function fetchOrganization(id: string) {
  return api.get<Organization>(`/system/organizations/${id}`);
}

export function createOrganization(data: OrgCreateData) {
  return api.post<Organization>("/system/organizations", data);
}

export function updateOrganization(id: string, data: OrgUpdateData) {
  return api.put<Organization>(`/system/organizations/${id}`, data);
}

export function deleteOrganization(id: string) {
  return api.delete(`/system/organizations/${id}`);
}

export function fetchTimezones() {
  return api.get<{ value: string; label: string }[]>(
    "/system/organizations/timezones",
  );
}

export function fetchOrgMembers(orgId: string) {
  return api.get<OrgMember[]>(`/system/organizations/${orgId}/members`);
}

export function uploadOrgLogo(orgId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post(`/system/organizations/${orgId}/logo`, formData);
}

// ============================================================================
// Invites
// ============================================================================

export interface Invite {
  id: string;
  email: string;
  org_id: string;
  org_role: string;
  status: "pending" | "accepted" | "expired" | "revoked";
  expires_at: string;
  created_at: string;
}

export function createInvite(data: { email: string; org_id: string; org_role: string }) {
  return api.post<Invite>("/invites", data);
}

export function fetchInvites(orgId: string) {
  return api.get<Invite[]>(`/invites?org_id=${orgId}`);
}

export function revokeInvite(inviteId: string) {
  return api.delete(`/invites/${inviteId}`);
}

export function resendInvite(inviteId: string) {
  return api.post<Invite>(`/invites/${inviteId}/resend`);
}

// ============================================================================
// System Agents
// ============================================================================

export function fetchSystemAgents() {
  return api.get<SystemAgent[]>("/system/agents");
}

export function createSystemAgent(data: AgentCreateData) {
  return api.post<SystemAgent>("/system/agents", data);
}

export function updateSystemAgent(id: string, data: AgentUpdateData) {
  return api.put<SystemAgent>(`/system/agents/${id}`, data);
}

export function deleteSystemAgent(id: string) {
  return api.delete(`/system/agents/${id}`);
}

// ============================================================================
// System Providers
// ============================================================================

export function fetchSystemProviders() {
  return api.get<SystemProvider[]>("/system/providers");
}

export function updateSystemProvider(id: string, data: ProviderUpdateData) {
  return api.put<SystemProvider>(`/system/providers/${id}`, data);
}

// ============================================================================
// System MCP Servers
// ============================================================================

export function fetchSystemMcpServers() {
  return api.get<SystemMcpServer[]>("/system/mcp-servers");
}

export function createSystemMcpServer(data: McpServerCreateData) {
  return api.post<SystemMcpServer>("/system/mcp-servers", data);
}

export function updateSystemMcpServer(id: string, data: McpServerUpdateData) {
  return api.put<SystemMcpServer>(`/system/mcp-servers/${id}`, data);
}

export function deleteSystemMcpServer(id: string) {
  return api.delete(`/system/mcp-servers/${id}`);
}

// ============================================================================
// System Settings
// ============================================================================

export function fetchSystemSettings() {
  return api.get<SystemSetting[]>("/system/settings");
}

export function updateSystemSetting(key: string, data: SettingUpdateData) {
  return api.put(`/system/settings/${key}`, data);
}
