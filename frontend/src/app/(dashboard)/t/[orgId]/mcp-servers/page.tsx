"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { PageHeader } from "@/components/shared/page-header";
import { PermissionGate } from "@/components/shared/permission-gate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Server, Settings2, ChevronDown, Wrench } from "lucide-react";
import { fetchAvailableMcpServers, fetchMcpServerTools } from "@/lib/api/tenant-mcp";
import type { AvailableMcpServer, McpToolResponse } from "@/types/models";
import { cn } from "@/lib/utils";

export default function TenantMcpServersPage() {
    const t = useTranslations("tenant");

    return (
        <PermissionGate permission="mcp_server.view" pageLevel>
            <div className="space-y-6">
                <PageHeader title={t("mcpServersTitle")} description={t("mcpPageDesc")} />
                <McpServersList />
            </div>
        </PermissionGate>
    );
}

function McpServersList() {
    const t = useTranslations("tenant");
    const { data: servers, isLoading } = useSWR("tenant-mcp-available", fetchAvailableMcpServers);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    if (isLoading) {
        return (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3].map((i) => (
                    <Card key={i} className="animate-pulse">
                        <CardContent className="p-6 h-32" />
                    </Card>
                ))}
            </div>
        );
    }

    if (!servers?.length) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
                    <Server className="h-12 w-12 text-muted-foreground/50" />
                    <p className="text-muted-foreground">{t("mcpPageNoServers")}</p>
                </CardContent>
            </Card>
        );
    }

    const toggle = (id: string) => setExpandedId(expandedId === id ? null : id);

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {servers.map((server) => (
                <McpServerCard
                    key={server.id}
                    server={server}
                    expanded={expandedId === server.id}
                    onToggle={() => toggle(server.id)}
                    t={t}
                />
            ))}
        </div>
    );
}

function McpServerCard({
    server, expanded, onToggle, t,
}: {
    server: AvailableMcpServer;
    expanded: boolean;
    onToggle: () => void;
    t: ReturnType<typeof useTranslations>;
}) {
    const { data: tools, isLoading } = useSWR<McpToolResponse[]>(
        expanded ? `mcp-tools-${server.id}` : null,
        () => fetchMcpServerTools(server.id),
    );

    return (
        <Card
            className={cn(
                "transition-all cursor-pointer hover:border-primary/30",
                expanded && "border-primary/40 ring-1 ring-primary/10 col-span-1 md:col-span-2 lg:col-span-3",
            )}
            onClick={onToggle}
        >
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Server className="h-4 w-4 text-primary" />
                        {server.display_name}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {server.is_system && (
                            <Badge variant="secondary" className="text-xs">
                                System
                            </Badge>
                        )}
                        {server.requires_env_vars && (
                            <Badge variant="outline" className="text-xs">
                                <Settings2 className="h-3 w-3 mr-1" />
                                {t("mcpEnvRequired")}
                            </Badge>
                        )}
                        <ChevronDown className={cn(
                            "h-4 w-4 text-muted-foreground transition-transform",
                            expanded && "rotate-180"
                        )} />
                    </div>
                </div>
                <CardDescription className="text-xs font-mono">
                    {server.codename}
                </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>{t("transport")}: {server.transport}</span>
                </div>

                {/* Expanded tool list */}
                {expanded && (
                    <div className="mt-4 border-t border-border/50 pt-4" onClick={(e) => e.stopPropagation()}>
                        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                            <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
                            Tools {tools ? `(${tools.length})` : ""}
                        </h4>
                        {isLoading ? (
                            <div className="space-y-2">
                                {[1, 2, 3].map((i) => (
                                    <div key={i} className="h-8 animate-pulse rounded bg-muted" />
                                ))}
                            </div>
                        ) : !tools?.length ? (
                            <p className="text-xs text-muted-foreground">{t("mcpPageNoServers")}</p>
                        ) : (
                            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                                {tools.map((tool) => (
                                    <div
                                        key={tool.id}
                                        className="rounded-lg border border-border/50 bg-muted/20 px-3 py-2"
                                    >
                                        <div className="text-sm font-medium">{tool.display_name}</div>
                                        <div className="text-xs text-muted-foreground font-mono">{tool.codename}</div>
                                        {tool.description && (
                                            <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                {tool.description}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
