"use client";

import { useTranslations } from "next-intl";
import type { Agent } from "@/types/models";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Bot, Globe, Shield, ChevronRight, AlertTriangle } from "lucide-react";

interface AgentListProps {
    agents: Agent[];
    selectedAgentId: string | null;
    onSelect: (agentId: string) => void;
}

export function AgentList({ agents, selectedAgentId, onSelect }: AgentListProps) {
    const t = useTranslations("tenant");

    return (
        <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                    <Bot className="h-4 w-4" /> {t("agentsTitle")}
                </CardTitle>
                <CardDescription className="text-xs">
                    {t("selectAgent")}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 max-h-[60vh] overflow-y-auto">
                {agents.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-8">{t("agentsNoData")}</p>
                )}
                {agents.map((agent) => (
                    <AgentListItem
                        key={agent.id}
                        agent={agent}
                        isSelected={selectedAgentId === agent.id}
                        onSelect={onSelect}
                    />
                ))}
            </CardContent>
        </Card>
    );
}

function AgentListItem({ agent, isSelected, onSelect }: {
    agent: Agent;
    isSelected: boolean;
    onSelect: (id: string) => void;
}) {
    return (
        <button
            type="button"
            onClick={() => onSelect(agent.id)}
            className={`flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-left transition-colors ${isSelected
                ? "bg-primary/10 border border-primary/20"
                : "hover:bg-muted/50 border border-transparent"
                }`}
        >
            <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{agent.display_name}</div>
                <div className="text-xs text-muted-foreground truncate">
                    {agent.codename}
                    {agent.model_name && (
                        <span className="ml-1 text-[10px] text-muted-foreground/70">• {agent.model_name}</span>
                    )}
                </div>
            </div>
            {!agent.has_provider && (
                <Badge variant="destructive" className="text-[10px] px-1.5 py-0 gap-0.5">
                    <AlertTriangle className="h-2.5 w-2.5" />No Provider
                </Badge>
            )}
            <AgentAccessBadge isPublic={agent.is_public} />
            {agent.is_system && (
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">System</Badge>
            )}
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </button>
    );
}

export function AgentAccessBadge({ isPublic }: { isPublic: boolean }) {
    const t = useTranslations("tenant");

    if (isPublic) {
        return (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                <Globe className="h-3 w-3 mr-0.5" />{t("public")}
            </Badge>
        );
    }
    return (
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
            <Shield className="h-3 w-3 mr-0.5" />{t("restricted")}
        </Badge>
    );
}
