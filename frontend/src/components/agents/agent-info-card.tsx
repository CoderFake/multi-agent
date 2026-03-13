"use client";

import { useTranslations } from "next-intl";
import type { Agent } from "@/types/models";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Globe, Shield } from "lucide-react";

interface AgentInfoCardProps {
    agent: Agent;
    onTogglePublic: (agent: Agent) => void;
}

export function AgentInfoCard({ agent, onTogglePublic }: AgentInfoCardProps) {
    const t = useTranslations("tenant");

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-lg">{agent.display_name}</CardTitle>
                        <CardDescription>{agent.description || agent.codename}</CardDescription>
                    </div>
                    <Button
                        variant={agent.is_public ? "default" : "outline"}
                        size="sm"
                        onClick={() => onTogglePublic(agent)}
                        className="gap-2"
                    >
                        {agent.is_public ? (
                            <><Globe className="h-4 w-4" /> {t("public")}</>
                        ) : (
                            <><Shield className="h-4 w-4" /> {t("restricted")}</>
                        )}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                <p className="text-xs text-muted-foreground">
                    {agent.is_public ? t("publicDesc") : t("restrictedDesc")}
                </p>
            </CardContent>
        </Card>
    );
}
