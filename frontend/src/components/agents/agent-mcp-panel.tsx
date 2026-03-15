"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import type { AgentMcpServer } from "@/types/models";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Plug, KeyRound, ChevronDown, ChevronRight, Save, AlertTriangle, Plus } from "lucide-react";
import { usePermissions } from "@/hooks/use-permissions";
import { updateMcpEnv } from "@/lib/api/agent-access";
import { AttachMcpModal } from "./attach-mcp-modal";

interface AgentMcpPanelProps {
    agentId: string;
    mcpServers: AgentMcpServer[];
    onMutate?: () => void;
}

/** Extract env key names from connection_config.mcpServers.*.env */
function extractEnvKeys(config: Record<string, unknown> | null): string[] {
    if (!config) return [];
    const servers = config.mcpServers as Record<string, { env?: Record<string, unknown> }> | undefined;
    if (!servers) return [];
    const keys = new Set<string>();
    for (const server of Object.values(servers)) {
        if (server.env) {
            for (const key of Object.keys(server.env)) {
                keys.add(key);
            }
        }
    }
    return Array.from(keys);
}

export function AgentMcpPanel({ agentId, mcpServers, onMutate }: AgentMcpPanelProps) {
    const t = useTranslations("tenant");
    const { hasPermission } = usePermissions();
    const [attachOpen, setAttachOpen] = useState(false);

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-base flex items-center gap-2">
                            <Plug className="h-4 w-4" /> {t("mcpServers")}
                        </CardTitle>
                        <CardDescription className="text-xs mt-1">
                            {t("mcpServersDesc")}
                        </CardDescription>
                    </div>
                    {hasPermission("agent_mcp.assign") && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setAttachOpen(true)}
                            className="gap-1.5 shrink-0"
                        >
                            <Plus className="h-3.5 w-3.5" />
                            {t("attachMcp")}
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {mcpServers.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">{t("noMcpServers")}</p>
                ) : (
                    <div className="space-y-2">
                        {mcpServers.map((mcp) => (
                            <McpServerItem key={mcp.id} mcp={mcp} onMutate={onMutate} />
                        ))}
                    </div>
                )}
            </CardContent>

            <AttachMcpModal
                open={attachOpen}
                onOpenChange={setAttachOpen}
                agentId={agentId}
                attached={mcpServers}
                onAttached={onMutate}
            />
        </Card>
    );
}

function McpServerItem({ mcp, onMutate }: { mcp: AgentMcpServer; onMutate?: () => void }) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);

    const envKeys = mcp.requires_env_vars ? extractEnvKeys(mcp.connection_config) : [];
    const hasEnvKeys = envKeys.length > 0;
    const currentOverrides = mcp.env_overrides ?? {};
    const missingKeys = envKeys.filter((k) => !currentOverrides[k]);

    // Local form state
    const [formValues, setFormValues] = useState<Record<string, string>>(() => {
        const values: Record<string, string> = {};
        for (const key of envKeys) {
            values[key] = currentOverrides[key] ?? "";
        }
        return values;
    });

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateMcpEnv(mcp.agent_id, mcp.mcp_server_id, formValues);
            toast.success(t("envVarsSaved"));
            onMutate?.();
        } catch {
            toast.error(tc("error"));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="rounded-lg border border-border/60 overflow-hidden">
            <div className="flex items-center gap-3 px-3 py-2">
                <Plug className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium">{mcp.mcp_server_name}</div>
                    <div className="text-xs text-muted-foreground">{mcp.mcp_server_codename}</div>
                </div>

                {/* Requires env vars badge */}
                {mcp.requires_env_vars && (
                    missingKeys.length > 0 ? (
                        <Badge variant="destructive" className="text-[10px] gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            {t("envRequired")}
                        </Badge>
                    ) : (
                        <Badge variant="secondary" className="text-[10px] gap-1">
                            <KeyRound className="h-3 w-3" />
                            {t("envConfigured")}
                        </Badge>
                    )
                )}

                <Badge variant={mcp.is_active ? "default" : "secondary"} className="text-[10px]">
                    {mcp.is_active ? t("active") : t("inactive")}
                </Badge>

                {/* Expand toggle for env form */}
                {mcp.requires_env_vars && hasEnvKeys && (
                    <Collapsible open={open} onOpenChange={setOpen}>
                        <CollapsibleTrigger className="p-1 rounded hover:bg-muted/50 transition-colors cursor-pointer">
                            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </CollapsibleTrigger>
                    </Collapsible>
                )}
            </div>

            {/* Env vars form */}
            {mcp.requires_env_vars && hasEnvKeys && open && (
                <div className="border-t border-border/40 bg-muted/20 px-3 py-3 space-y-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <KeyRound className="h-3.5 w-3.5" />
                        {t("envVarsForAgent")}
                    </div>
                    <div className="space-y-2">
                        {envKeys.map((key) => (
                            <div key={key} className="flex items-center gap-2">
                                <label className="text-xs font-mono text-primary/80 w-40 shrink-0 truncate" title={key}>
                                    {key}
                                </label>
                                <Input
                                    type="password"
                                    value={formValues[key] ?? ""}
                                    onChange={(e) => setFormValues((prev) => ({ ...prev, [key]: e.target.value }))}
                                    placeholder={`Enter ${key}`}
                                    className="h-8 text-xs font-mono"
                                />
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-end">
                        <Button size="sm" onClick={handleSave} disabled={saving} className="gap-1.5">
                            <Save className="h-3.5 w-3.5" />
                            {tc("save")}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
