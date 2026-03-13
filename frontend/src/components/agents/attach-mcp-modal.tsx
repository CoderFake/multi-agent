"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { toast } from "sonner";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Plug, Search, Plus, Loader2 } from "lucide-react";
import { fetchAvailableMcpServers, attachMcpToAgent } from "@/lib/api/agent-access";
import type { AgentMcpServer, AvailableMcpServer } from "@/types/models";

interface AttachMcpModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    agentId: string;
    /** Already-attached MCP servers, to filter them out of the list. */
    attached: AgentMcpServer[];
    onAttached?: () => void;
}

export function AttachMcpModal({ open, onOpenChange, agentId, attached, onAttached }: AttachMcpModalProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [search, setSearch] = useState("");
    const [attaching, setAttaching] = useState<string | null>(null);

    const { data: available, isLoading } = useSWR(
        open ? "available-mcp-servers" : null,
        fetchAvailableMcpServers,
    );

    // Filter out already-attached servers
    const attachedIds = useMemo(() => new Set(attached.map((m) => m.mcp_server_id)), [attached]);

    const filtered = useMemo(() => {
        if (!available) return [];
        return available
            .filter((s) => !attachedIds.has(s.id))
            .filter((s) =>
                s.display_name.toLowerCase().includes(search.toLowerCase()) ||
                s.codename.toLowerCase().includes(search.toLowerCase()),
            );
    }, [available, attachedIds, search]);

    const handleAttach = async (server: AvailableMcpServer) => {
        setAttaching(server.id);
        try {
            await attachMcpToAgent(agentId, server.id);
            toast.success(t("mcpAttached"));
            onAttached?.();
            // If no more servers to attach, close
            if (filtered.length <= 1) {
                onOpenChange(false);
            }
        } catch {
            toast.error(tc("error"));
        } finally {
            setAttaching(null);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Plug className="h-4 w-4" />
                        {t("attachMcpTitle")}
                    </DialogTitle>
                    <DialogDescription>{t("attachMcpDesc")}</DialogDescription>
                </DialogHeader>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder={tc("search")}
                        className="pl-9 h-9"
                    />
                </div>

                {/* Server list */}
                <ScrollArea className="h-60 rounded-md">
                    <div className="space-y-1 p-1">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                            </div>
                        ) : filtered.length === 0 ? (
                            <p className="text-xs text-muted-foreground text-center py-8">
                                {t("noAvailableMcp")}
                            </p>
                        ) : (
                            filtered.map((server) => (
                                <div
                                    key={server.id}
                                    className="flex items-center gap-3 rounded-md px-3 py-2 hover:bg-muted/50 transition-colors"
                                >
                                    <Plug className="h-4 w-4 text-muted-foreground shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm font-medium truncate">
                                            {server.display_name}
                                        </div>
                                        <div className="text-xs text-muted-foreground truncate">
                                            {server.codename}
                                        </div>
                                    </div>
                                    <Badge variant="outline" className="text-[10px] shrink-0">
                                        {server.transport}
                                    </Badge>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => handleAttach(server)}
                                        disabled={attaching === server.id}
                                        className="shrink-0 gap-1"
                                    >
                                        {attaching === server.id ? (
                                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        ) : (
                                            <Plus className="h-3.5 w-3.5" />
                                        )}
                                        {t("attach")}
                                    </Button>
                                </div>
                            ))
                        )}
                    </div>
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
}
