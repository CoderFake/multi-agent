"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { PermissionGate } from "@/components/shared/permission-gate";
import { AgentList } from "@/components/agents/agent-list";
import { AgentInfoCard } from "@/components/agents/agent-info-card";
import { AgentMcpPanel } from "@/components/agents/agent-mcp-panel";
import { AgentGroupAccess } from "@/components/agents/agent-group-access";
import { CreateAgentDialog, CreateAgentButton } from "@/components/agents/create-agent-dialog";
import {
    useAgents,
    useAgentMcpServers,
    useGroups,
    useAgentGroups,
    useToggleAgentPublic,
    useAssignAgentToGroup,
    useRevokeAgentFromGroup,
} from "@/hooks/use-agent-access";
import { Bot, Filter, Check } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

type AgentFilter = "all" | "system" | "tenant";

export default function TenantAgentsPage() {
    const t = useTranslations("tenant");
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
    const [createOpen, setCreateOpen] = useState(false);
    const [filter, setFilter] = useState<AgentFilter>("all");

    // Data hooks
    const { agents: allAgents, mutateAgents } = useAgents();
    const { mcpServers, mutateMcps } = useAgentMcpServers(selectedAgentId);
    const { groups } = useGroups();
    const { agentGroups, mutateAgentGroups } = useAgentGroups(selectedAgentId, groups);

    // Action hooks
    const handleTogglePublic = useToggleAgentPublic(mutateAgents);
    const handleAssignGroup = useAssignAgentToGroup(mutateAgentGroups);
    const handleRevokeGroup = useRevokeAgentFromGroup(mutateAgentGroups);

    // Filter agents
    const agents = allAgents.filter((a) => {
        if (filter === "system") return a.is_system;
        if (filter === "tenant") return !a.is_system;
        return true;
    });

    const selectedAgent = agents.find((a) => a.id === selectedAgentId);

    return (
        <div className="space-y-4">
            <PageHeader title={t("agentsTitle")} description={t("agentsDesc")}>
                <div className="flex items-center gap-2">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm" className="gap-2">
                                <Filter className="h-4 w-4" />
                                {filter === "all"
                                    ? t("allAgents")
                                    : filter === "system"
                                      ? t("systemAgents")
                                      : t("tenantAgents")}
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setFilter("all")} className="gap-2">
                                {filter === "all" && <Check className="h-3.5 w-3.5" />}
                                {t("allAgents")}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setFilter("system")} className="gap-2">
                                {filter === "system" && <Check className="h-3.5 w-3.5" />}
                                {t("systemAgents")}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setFilter("tenant")} className="gap-2">
                                {filter === "tenant" && <Check className="h-3.5 w-3.5" />}
                                {t("tenantAgents")}
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>

                    <PermissionGate permission="agent.create">
                        <CreateAgentButton onClick={() => setCreateOpen(true)} />
                    </PermissionGate>
                </div>
            </PageHeader>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <AgentList
                    agents={agents}
                    selectedAgentId={selectedAgentId}
                    onSelect={setSelectedAgentId}
                />

                <div className="lg:col-span-2 space-y-4">
                    {!selectedAgent ? (
                        <Card>
                            <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                                <Bot className="h-10 w-10 mb-3 opacity-30" />
                                <p className="text-sm">{t("selectAgent")}</p>
                            </CardContent>
                        </Card>
                    ) : (
                        <>
                            <AgentInfoCard agent={selectedAgent} onTogglePublic={handleTogglePublic} />

                            {/* MCP panel — ONLY for tenant agents, NOT system agents */}
                            {!selectedAgent.is_system && (
                                <AgentMcpPanel agentId={selectedAgent.id} mcpServers={mcpServers} onMutate={mutateMcps} />
                            )}

                            {!selectedAgent.is_public && (
                                <AgentGroupAccess
                                    agentGroups={agentGroups}
                                    groups={groups}
                                    onAssign={(groupId) => handleAssignGroup(groupId, selectedAgent.id)}
                                    onRevoke={(groupId) => handleRevokeGroup(groupId, selectedAgent.id)}
                                />
                            )}
                        </>
                    )}
                </div>
            </div>

            <CreateAgentDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCreated={mutateAgents}
            />
        </div>
    );
}
