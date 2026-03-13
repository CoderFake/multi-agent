"use client";

import { useTranslations } from "next-intl";
import type { AgentMcpServer } from "@/types/models";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Plug } from "lucide-react";

interface AgentMcpPanelProps {
    mcpServers: AgentMcpServer[];
}

export function AgentMcpPanel({ mcpServers }: AgentMcpPanelProps) {
    const t = useTranslations("tenant");

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                    <Plug className="h-4 w-4" /> {t("mcpServers")}
                </CardTitle>
                <CardDescription className="text-xs">
                    {t("mcpServersDesc")}
                </CardDescription>
            </CardHeader>
            <CardContent>
                {mcpServers.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">{t("noMcpServers")}</p>
                ) : (
                    <div className="space-y-2">
                        {mcpServers.map((mcp) => (
                            <McpServerItem key={mcp.id} mcp={mcp} />
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function McpServerItem({ mcp }: { mcp: AgentMcpServer }) {
    const t = useTranslations("tenant");

    return (
        <div className="flex items-center gap-3 rounded-lg border border-border/60 px-3 py-2">
            <Plug className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{mcp.mcp_server_name}</div>
                <div className="text-xs text-muted-foreground">{mcp.mcp_server_codename}</div>
            </div>
            <Badge variant={mcp.is_active ? "default" : "secondary"} className="text-[10px]">
                {mcp.is_active ? t("active") : t("inactive")}
            </Badge>
        </div>
    );
}
