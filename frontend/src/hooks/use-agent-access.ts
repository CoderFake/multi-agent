/**
 * Agent access control data hooks.
 * Encapsulates SWR fetching + mutation for agent access control.
 */
import { useCallback } from "react";
import useSWR from "swr";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import {
    fetchTenantAgents,
    fetchAgentMcpServers,
    toggleAgentPublic,
    fetchGroupAgents,
    assignAgentsToGroup,
    revokeAgentFromGroup,
} from "@/lib/api/agent-access";
import { fetchTenantGroups } from "@/lib/api/tenant";
import type { Agent, AgentMcpServer, GroupAgent, Group } from "@/types/models";

/** Fetch enabled agents for the org. */
export function useAgents() {
    const { orgId } = useCurrentOrg();
    const { data, mutate, isLoading } = useSWR(
        orgId ? ["tenant-agents", orgId] : null,
        () => fetchTenantAgents(),
    );
    const agents = data?.filter((a: Agent) => a.is_enabled) ?? [];
    return { agents, mutateAgents: mutate, isLoading };
}

/** Fetch MCP servers attached to an agent. */
export function useAgentMcpServers(agentId: string | null) {
    const { orgId } = useCurrentOrg();
    const { hasPermission } = usePermissions();
    const canViewMcp = hasPermission("agent_mcp.view");
    const { data, mutate, isLoading } = useSWR(
        agentId && orgId && canViewMcp ? ["agent-mcps", agentId, orgId] : null,
        () => fetchAgentMcpServers(agentId!),
    );
    return { mcpServers: data ?? [], mutateMcps: mutate, isLoading };
}

/** Fetch groups for the org. */
export function useGroups() {
    const { orgId } = useCurrentOrg();
    const { hasPermission } = usePermissions();
    const canViewGroups = hasPermission("group.view");
    const { data, isLoading } = useSWR(
        orgId && canViewGroups ? ["tenant-groups-list", orgId] : null,
        () => fetchTenantGroups(),
    );
    const groups: Group[] = data?.items ?? [];
    return { groups, isLoading };
}

/** Fetch groups that have access to a specific agent. */
export function useAgentGroups(agentId: string | null, groups: Group[]) {
    const { orgId } = useCurrentOrg();
    const { data, mutate, isLoading } = useSWR(
        agentId && orgId && groups.length > 0 ? ["agent-groups", agentId, orgId] : null,
        async () => {
            const results: (GroupAgent & { group_name: string })[] = [];
            for (const g of groups) {
                const ga = await fetchGroupAgents(g.id);
                for (const item of ga) {
                    if (item.agent_id === agentId) {
                        results.push({ ...item, group_name: g.name });
                    }
                }
            }
            return results;
        },
    );
    return { agentGroups: data ?? [], mutateAgentGroups: mutate, isLoading };
}

/** Toggle agent public/restricted. */
export function useToggleAgentPublic(mutateAgents: () => void) {
    const t = useTranslations("tenant");

    return useCallback(async (agent: Agent) => {
        try {
            await toggleAgentPublic(agent.id, !agent.is_public);
            toast.success(agent.is_public ? t("agentSetRestricted") : t("agentSetPublic"));
            mutateAgents();
        } catch {
            toast.error(t("error"));
        }
    }, [mutateAgents, t]);
}

/** Assign an agent to multiple groups at once. */
export function useAssignAgentToGroups(mutateAgentGroups: () => void) {
    const t = useTranslations("tenant");

    return useCallback(async (groupIds: string[], agentId: string) => {
        try {
            await Promise.all(groupIds.map((gid) => assignAgentsToGroup(gid, [agentId])));
            toast.success(t("groupAssigned"));
            mutateAgentGroups();
        } catch {
            toast.error(t("error"));
        }
    }, [mutateAgentGroups, t]);
}

/** Revoke agent from group. */
export function useRevokeAgentFromGroup(mutateAgentGroups: () => void) {
    const t = useTranslations("tenant");

    return useCallback(async (groupId: string, agentId: string) => {
        try {
            await revokeAgentFromGroup(groupId, agentId);
            toast.success(t("groupRevoked"));
            mutateAgentGroups();
        } catch {
            toast.error(t("error"));
        }
    }, [mutateAgentGroups, t]);
}
