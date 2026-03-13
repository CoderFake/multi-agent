/**
 * Tenant Agent Access Control API — agent-MCP, group-agent, group-tool.
 */
import { api } from "@/lib/api-client";
import type { Agent, AgentCreate, AgentUpdate, AgentMcpServer, GroupAgent, GroupToolAccess, AvailableMcpServer } from "@/types/models";

// ── Available MCP servers for the org ────────────────────────────────────

export function fetchAvailableMcpServers() {
    return api.get<AvailableMcpServer[]>("/tenant/access/available-mcp-servers");
}

// ── Agents CRUD ─────────────────────────────────────────────────────────

export function fetchTenantAgents() {
    return api.get<Agent[]>("/tenant/agents");
}

export function createTenantAgent(data: AgentCreate) {
    return api.post<Agent>("/tenant/agents", data);
}

export function updateTenantAgent(agentId: string, data: AgentUpdate) {
    return api.put<Agent>(`/tenant/agents/${agentId}`, data);
}

export function deleteTenantAgent(agentId: string) {
    return api.delete(`/tenant/agents/${agentId}`);
}

export function enableSystemAgent(agentId: string) {
    return api.post<{ status: string; agent_id: string }>(`/tenant/agents/system/${agentId}/enable`);
}

export function disableSystemAgent(agentId: string) {
    return api.post<{ status: string; agent_id: string }>(`/tenant/agents/system/${agentId}/disable`);
}
// ── Agent ↔ MCP Server ─────────────────────────────────────────────────

export function fetchAgentMcpServers(agentId: string) {
    return api.get<AgentMcpServer[]>(`/tenant/access/agents/${agentId}/mcp-servers`);
}

export function attachMcpToAgent(agentId: string, mcpServerId: string) {
    return api.post<AgentMcpServer>(`/tenant/access/agents/${agentId}/mcp-servers`, {
        mcp_server_id: mcpServerId,
    });
}

export function detachMcpFromAgent(agentId: string, mcpServerId: string) {
    return api.delete(`/tenant/access/agents/${agentId}/mcp-servers/${mcpServerId}`);
}

export function updateMcpEnv(agentId: string, mcpServerId: string, envOverrides: Record<string, string>) {
    return api.patch(`/tenant/access/agents/${agentId}/mcp-servers/${mcpServerId}/env`, {
        env_overrides: envOverrides,
    });
}

// ── Agent is_public ─────────────────────────────────────────────────────

export function toggleAgentPublic(agentId: string, isPublic: boolean) {
    return api.patch<{ agent_id: string; is_public: boolean }>(
        `/tenant/access/agents/${agentId}/public`,
        { is_public: isPublic },
    );
}

// ── Group ↔ Agent ───────────────────────────────────────────────────────

export function fetchGroupAgents(groupId: string) {
    return api.get<GroupAgent[]>(`/tenant/access/groups/${groupId}/agents`);
}

export function assignAgentsToGroup(groupId: string, agentIds: string[]) {
    return api.post<GroupAgent[]>(`/tenant/access/groups/${groupId}/agents`, { agent_ids: agentIds });
}

export function revokeAgentFromGroup(groupId: string, agentId: string) {
    return api.delete(`/tenant/access/groups/${groupId}/agents/${agentId}`);
}

// ── Group ↔ Tool Access ─────────────────────────────────────────────────

export function fetchGroupToolAccess(groupId: string) {
    return api.get<GroupToolAccess[]>(`/tenant/access/groups/${groupId}/tools`);
}

export function toggleToolAccess(groupId: string, toolId: string, isEnabled: boolean) {
    return api.patch<GroupToolAccess>(`/tenant/access/groups/${groupId}/tools/${toolId}`, {
        tool_id: toolId,
        is_enabled: isEnabled,
    });
}

export function bulkToggleTools(groupId: string, entries: { tool_id: string; is_enabled: boolean }[]) {
    return api.put<GroupToolAccess[]>(`/tenant/access/groups/${groupId}/tools`, { entries });
}
