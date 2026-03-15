/**
 * Tenant Provider API — provider keys, models, agent-provider mapping.
 * All calls use X-Org-Id header (auto-attached by api-client).
 */
import { api } from "@/lib/api-client";
import type {
    SystemProvider,
    ProviderKey,
    ProviderKeyCreate,
    ProviderKeyUpdate,
    AgentModel,
    AgentProviderMapping,
    AgentProviderCreate,
    AgentProviderUpdate,
} from "@/types/models";

// ── Available Providers ─────────────────────────────────────────────────

export function fetchTenantProviders() {
    return api.get<SystemProvider[]>("/tenant/providers");
}

// ── Provider Keys ─────────────────────────────────────────────────────

export function fetchProviderKeys(providerId: string) {
    return api.get<ProviderKey[]>(`/tenant/providers/${providerId}/keys`);
}

export function addProviderKey(providerId: string, data: ProviderKeyCreate) {
    return api.post<ProviderKey>(`/tenant/providers/${providerId}/keys`, data);
}

export function updateProviderKey(keyId: string, data: ProviderKeyUpdate) {
    return api.put<ProviderKey>(`/tenant/providers/keys/${keyId}`, data);
}

export function deleteProviderKey(keyId: string) {
    return api.delete(`/tenant/providers/keys/${keyId}`);
}

// ── Provider Models ─────────────────────────────────────────────────────

export function fetchProviderModels(providerId: string) {
    return api.get<AgentModel[]>(`/tenant/providers/${providerId}/models`);
}

// ── Agent-Provider Mapping ──────────────────────────────────────────────

export function fetchAgentMappings() {
    return api.get<AgentProviderMapping[]>("/tenant/providers/agent-mapping");
}

export function createAgentMapping(data: AgentProviderCreate) {
    return api.post<AgentProviderMapping>("/tenant/providers/agent-mapping", data);
}

export function updateAgentMapping(mappingId: string, data: AgentProviderUpdate) {
    return api.put<AgentProviderMapping>(`/tenant/providers/agent-mapping/${mappingId}`, data);
}

export function deleteAgentMapping(mappingId: string) {
    return api.delete(`/tenant/providers/agent-mapping/${mappingId}`);
}
