/**
 * Tenant MCP Server API — org-scoped MCP server + tool management.
 * All calls use X-Org-Id header (auto-attached by api-client).
 */
import { api } from "@/lib/api-client";
import type {
    AgentMcpServer,
    AvailableMcpServer,
    McpToolResponse,
} from "@/types/models";

// ── Agent MCP Servers ───────────────────────────────────────────────────

export function fetchAgentMcpServers(agentId: string) {
    return api.get<AgentMcpServer[]>(`/tenant/access/agents/${agentId}/mcp-servers`);
}

export function assignMcpToAgent(agentId: string, mcpServerId: string, envOverrides?: Record<string, string>) {
    return api.post(`/tenant/access/agents/${agentId}/mcp-servers`, {
        mcp_server_id: mcpServerId,
        env_overrides: envOverrides || null,
    });
}

export function revokeMcpFromAgent(agentId: string, mcpServerId: string) {
    return api.delete(`/tenant/access/agents/${agentId}/mcp-servers/${mcpServerId}`);
}

export function updateMcpEnvOverrides(agentId: string, mcpServerId: string, envOverrides: Record<string, string> | null) {
    return api.put(`/tenant/access/agents/${agentId}/mcp-servers/${mcpServerId}/env`, {
        env_overrides: envOverrides,
    });
}

// ── Available MCP Servers ───────────────────────────────────────────────

export function fetchAvailableMcpServers() {
    return api.get<AvailableMcpServer[]>("/tenant/mcp-servers/available");
}

// ── Agent Tools ─────────────────────────────────────────────────────────

export function fetchAgentTools(agentId: string) {
    return api.get<McpToolResponse[]>(`/tenant/access/agents/${agentId}/tools`);
}

// ── Tenant MCP Servers (custom) ─────────────────────────────────────────

export function fetchTenantMcpServers() {
    return api.get<AgentMcpServer[]>("/tenant/mcp-servers");
}

// ── MCP Server Tools ────────────────────────────────────────────────────

export function fetchMcpServerTools(serverId: string) {
    return api.get<McpToolResponse[]>(`/tenant/mcp-servers/${serverId}/tools`);
}
