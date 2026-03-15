"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Wrench, Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
    fetchAgentTools, fetchGroupToolAccess, bulkToggleTools,
} from "@/lib/api/agent-access";

import type { GroupToolAccess, AgentTool } from "@/types/models";

interface AssignToolDialogProps {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    groupId: string;
    agentId: string;
    orgId: string;
    onSaved: () => void;
}

export function AssignToolDialog({ open, onOpenChange, groupId, agentId, orgId, onSaved }: AssignToolDialogProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [search, setSearch] = useState("");
    const [enabledTools, setEnabledTools] = useState<Set<string>>(new Set());
    const [saving, setSaving] = useState(false);
    const [initialized, setInitialized] = useState(false);

    // Fetch all tools for this agent — always fresh when modal opens
    const { data: agentTools, isLoading: loadingTools } = useSWR(
        open && agentId ? ["agent-tools", agentId] : null,
        () => fetchAgentTools(agentId),
        { revalidateOnMount: true, dedupingInterval: 0 },
    );

    // Fetch current tool access settings for this group+agent
    const { data: currentAccess, isLoading: loadingAccess } = useSWR(
        open && groupId && agentId ? ["group-tool-access", groupId, agentId, orgId] : null,
        () => fetchGroupToolAccess(groupId, agentId),
        { revalidateOnMount: true, dedupingInterval: 0 },
    );

    // Initialize enabled set from current access
    useEffect(() => {
        if (!agentTools || loadingAccess || initialized) return;

        if (!currentAccess || currentAccess.length === 0) {
            // No records = all tools enabled (default)
            setEnabledTools(new Set(agentTools.map((t) => t.id)));
        } else {
            // Use existing records
            const enabled = new Set<string>();
            for (const access of currentAccess) {
                if (access.is_enabled) {
                    enabled.add(access.tool_id);
                }
            }
            // Tools without a record are considered enabled (default allow)
            const recordedToolIds = new Set(currentAccess.map((a) => a.tool_id));
            for (const tool of agentTools) {
                if (!recordedToolIds.has(tool.id)) {
                    enabled.add(tool.id);
                }
            }
            setEnabledTools(enabled);
        }
        setInitialized(true);
    }, [agentTools, currentAccess, loadingAccess, initialized]);

    const tools = agentTools ?? [];
    const filteredTools = tools.filter((t) =>
        t.display_name.toLowerCase().includes(search.toLowerCase()) ||
        t.codename.toLowerCase().includes(search.toLowerCase())
    );

    const allSelected = filteredTools.length > 0 && filteredTools.every((t) => enabledTools.has(t.id));

    const toggleTool = (toolId: string) => {
        setEnabledTools((prev) => {
            const next = new Set(prev);
            if (next.has(toolId)) {
                next.delete(toolId);
            } else {
                next.add(toolId);
            }
            return next;
        });
    };

    const toggleAll = () => {
        if (allSelected) {
            setEnabledTools(new Set());
        } else {
            setEnabledTools(new Set(tools.map((t) => t.id)));
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const entries = tools.map((tool) => ({
                tool_id: tool.id,
                is_enabled: enabledTools.has(tool.id),
            }));
            await bulkToggleTools(groupId, agentId, entries);
            toast.success(t("toolAccessSaved"));
            onSaved();
            onOpenChange(false);
        } catch {
            toast.error(t("error"));
        } finally {
            setSaving(false);
        }
    };

    const handleOpenChange = (v: boolean) => {
        if (!v) {
            setSearch("");
            setEnabledTools(new Set());
            setInitialized(false);
        }
        onOpenChange(v);
    };

    const isLoading = loadingTools || loadingAccess;

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="max-w-md max-h-[85vh] flex flex-col overflow-hidden">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Wrench className="h-4 w-4" /> {t("assignTools")}
                    </DialogTitle>
                    <DialogDescription>{t("assignToolsDesc")}</DialogDescription>
                </DialogHeader>

                {isLoading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                ) : tools.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">{t("noToolsAvailable")}</p>
                ) : (
                    <div className="space-y-3">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder={t("searchTools")}
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-8 h-9"
                            />
                        </div>

                        <div className="flex items-center justify-between px-1">
                            <div className="flex items-center gap-2">
                                <Checkbox
                                    id="select-all-tools"
                                    checked={allSelected}
                                    onCheckedChange={toggleAll}
                                />
                                <Label htmlFor="select-all-tools" className="text-xs text-muted-foreground cursor-pointer">
                                    {t("selectAll")} ({tools.length})
                                </Label>
                            </div>
                            <span className="text-xs text-muted-foreground">
                                {enabledTools.size}/{tools.length} {t("toolsEnabled")}
                            </span>
                        </div>

                        <ScrollArea className="h-[280px]">
                            <div className="space-y-1">
                                {filteredTools.map((tool) => (
                                    <label
                                        key={tool.id}
                                        className="flex items-center gap-3 rounded-md px-3 py-2 cursor-pointer hover:bg-muted/50 transition-colors"
                                    >
                                        <Checkbox
                                            checked={enabledTools.has(tool.id)}
                                            onCheckedChange={() => toggleTool(tool.id)}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium truncate">{tool.display_name}</div>
                                            <div className="text-xs text-muted-foreground truncate">{tool.codename}</div>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>
                )}

                <DialogFooter>
                    <Button variant="outline" onClick={() => handleOpenChange(false)}>{tc("cancel")}</Button>
                    <Button onClick={handleSave} disabled={saving || isLoading}>
                        {saving && <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />}
                        {tc("save")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
