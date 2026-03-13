"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Building2, Save } from "lucide-react";
import { fetchOrganizations, fetchMcpAssignedOrgs, setMcpAssignedOrgs } from "@/lib/api/system";

interface McpOrgAssignModalProps {
    serverId: string | null;
    serverName: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function McpOrgAssignModal({
    serverId,
    serverName,
    open,
    onOpenChange,
}: McpOrgAssignModalProps) {
    const t = useTranslations("common");
    const ts = useTranslations("system");
    const [search, setSearch] = useState("");
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [saving, setSaving] = useState(false);

    // Fetch all orgs
    const { data: orgPage } = useSWR(
        open ? "system-orgs-for-assign" : null,
        () => fetchOrganizations({ page: 1, pageSize: 200 }),
    );
    const orgs = orgPage?.items ?? [];

    // Fetch currently assigned orgs
    const { data: assignedOrgIds } = useSWR(
        open && serverId ? `mcp-assigned-orgs-${serverId}` : null,
        () => fetchMcpAssignedOrgs(serverId!),
    );

    // Sync assigned orgs to local state
    useEffect(() => {
        if (assignedOrgIds) {
            setSelected(new Set(assignedOrgIds));
        }
    }, [assignedOrgIds]);

    const toggle = useCallback((orgId: string) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(orgId)) next.delete(orgId);
            else next.add(orgId);
            return next;
        });
    }, []);

    const selectAll = useCallback(() => {
        setSelected(new Set(orgs.map((o) => o.id)));
    }, [orgs]);

    const deselectAll = useCallback(() => {
        setSelected(new Set());
    }, []);

    const handleSave = async () => {
        if (!serverId) return;
        setSaving(true);
        try {
            await setMcpAssignedOrgs(serverId, Array.from(selected));
            toast.success(ts("mcpOrgsAssigned"));
            onOpenChange(false);
        } catch {
            toast.error(t("error"));
        } finally {
            setSaving(false);
        }
    };

    const filtered = orgs.filter(
        (o) =>
            o.name.toLowerCase().includes(search.toLowerCase()) ||
            o.slug?.toLowerCase().includes(search.toLowerCase()),
    );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Building2 className="h-4 w-4" />
                        {ts("assignOrgs")}
                    </DialogTitle>
                    <DialogDescription>
                        {ts("assignOrgsDesc", { name: serverName })}
                    </DialogDescription>
                </DialogHeader>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder={ts("searchOrgs")}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-9 h-9"
                    />
                </div>

                {/* Select all / deselect all */}
                <div className="flex gap-2 text-xs">
                    <Button variant="ghost" size="sm" onClick={selectAll} className="h-7 text-xs">
                        {ts("selectAll")}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={deselectAll} className="h-7 text-xs">
                        {ts("deselectAll")}
                    </Button>
                    <span className="ml-auto text-muted-foreground self-center">
                        {selected.size}/{orgs.length}
                    </span>
                </div>

                {/* Org list */}
                <ScrollArea className="h-60 rounded-md">
                    <div className="p-2 space-y-1">
                        {filtered.length === 0 ? (
                            <p className="text-xs text-muted-foreground text-center py-4">
                                {t("noData")}
                            </p>
                        ) : (
                            filtered.map((org) => (
                                <label
                                    key={org.id}
                                    className="flex items-center gap-3 rounded-md px-2 py-1.5 hover:bg-muted/50 cursor-pointer transition-colors"
                                >
                                    <Checkbox
                                        checked={selected.has(org.id)}
                                        onCheckedChange={() => toggle(org.id)}
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm font-medium truncate">{org.name}</div>
                                        {org.slug && (
                                            <div className="text-xs text-muted-foreground truncate">
                                                {org.slug}
                                            </div>
                                        )}
                                    </div>
                                </label>
                            ))
                        )}
                    </div>
                </ScrollArea>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        {t("cancel")}
                    </Button>
                    <Button onClick={handleSave} disabled={saving} className="gap-1.5">
                        <Save className="h-3.5 w-3.5" />
                        {t("save")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
