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
import { Bot } from "lucide-react";

export default function TenantAgentsPage() {
    const t = useTranslations("tenant");
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
    const [createOpen, setCreateOpen] = useState(false);

    // Data hooks
    const { agents, mutateAgents } = useAgents();
    const { mcpServers } = useAgentMcpServers(selectedAgentId);
    const { groups } = useGroups();
    const { agentGroups, mutateAgentGroups } = useAgentGroups(selectedAgentId, groups);

    // Action hooks
    const handleTogglePublic = useToggleAgentPublic(mutateAgents);
    const handleAssignGroup = useAssignAgentToGroup(mutateAgentGroups);
    const handleRevokeGroup = useRevokeAgentFromGroup(mutateAgentGroups);

    const selectedAgent = agents.find((a) => a.id === selectedAgentId);

    return (
        <div className="space-y-4">
            <PageHeader title={t("agentsTitle")} description={t("agentsDesc")}>
                <PermissionGate permission="agent.create">
                    <CreateAgentButton onClick={() => setCreateOpen(true)} />
                </PermissionGate>
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
                            <AgentMcpPanel mcpServers={mcpServers} />
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
