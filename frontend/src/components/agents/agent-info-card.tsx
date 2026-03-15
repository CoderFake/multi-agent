"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { Agent } from "@/types/models";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Globe, Shield, Pencil } from "lucide-react";
import { usePermissions } from "@/hooks/use-permissions";
import { EditAgentDialog } from "./edit-agent-dialog";

interface AgentInfoCardProps {
    agent: Agent;
    onTogglePublic: (agent: Agent) => void;
    onUpdated?: () => void;
}

export function AgentInfoCard({ agent, onTogglePublic, onUpdated }: AgentInfoCardProps) {
    const t = useTranslations("tenant");
    const { hasPermission } = usePermissions();
    const [editOpen, setEditOpen] = useState(false);

    return (
        <>
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-lg">{agent.display_name}</CardTitle>
                            <CardDescription>{agent.description || agent.codename}</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            {/* Edit button — configure provider for system, full edit for custom */}
                            {hasPermission("agent.update") && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setEditOpen(true)}
                                    className="gap-1.5"
                                >
                                    <Pencil className="h-3.5 w-3.5" />
                                    {agent.is_system ? t("configureProvider") : t("editAgent")}
                                </Button>
                            )}

                            {/* Public / Restricted toggle */}
                            {hasPermission("agent.update") && (
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
                            )}
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <p className="text-xs text-muted-foreground">
                        {agent.is_public ? t("publicDesc") : t("restrictedDesc")}
                    </p>
                </CardContent>
            </Card>

            {/* Edit dialog */}
            <EditAgentDialog
                agent={agent}
                open={editOpen}
                onOpenChange={setEditOpen}
                onUpdated={() => onUpdated?.()}
            />
        </>
    );
}
