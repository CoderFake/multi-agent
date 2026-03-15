"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { GroupAgent, Group } from "@/types/models";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Users, Search, Wrench } from "lucide-react";
import { Input } from "@/components/ui/input";
import { usePermissions } from "@/hooks/use-permissions";
import { AssignToolDialog } from "./assign-tool-dialog";

interface AgentGroupAccessItem extends GroupAgent {
    group_name: string;
}

interface AgentGroupAccessProps {
    agentId: string;
    orgId: string;
    agentGroups: AgentGroupAccessItem[];
    groups: Group[];
    onAssignMultiple: (groupIds: string[]) => void;
    onRevoke: (groupId: string) => void;
}

export function AgentGroupAccess({ agentId, orgId, agentGroups, groups, onAssignMultiple, onRevoke }: AgentGroupAccessProps) {
    const t = useTranslations("tenant");
    const { hasPermission } = usePermissions();
    const [assignOpen, setAssignOpen] = useState(false);
    const [toolDialogGroupId, setToolDialogGroupId] = useState<string | null>(null);

    // Filter out groups that are already assigned
    const assignedGroupIds = new Set(agentGroups.map((ga) => ga.group_id));
    const availableGroups = groups.filter((g) => !assignedGroupIds.has(g.id));

    const handleAssign = (groupIds: string[]) => {
        if (groupIds.length === 0) return;
        onAssignMultiple(groupIds);
        setAssignOpen(false);
    };

    return (
        <>
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-base flex items-center gap-2">
                                <Users className="h-4 w-4" /> {t("groupAccess")}
                            </CardTitle>
                            <CardDescription className="text-xs">
                                {t("groupAccessDesc")}
                            </CardDescription>
                        </div>
                        {hasPermission("agent.update") && (
                            <Button size="sm" variant="outline" onClick={() => setAssignOpen(true)} className="gap-1.5" disabled={availableGroups.length === 0}>
                                <Users className="h-3.5 w-3.5" /> {t("assignGroup")}
                            </Button>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    {agentGroups.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            {t("noGroupsAssigned")}
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {agentGroups.map((ga) => (
                                <GroupAccessItem
                                    key={ga.id}
                                    item={ga}
                                    onRevoke={onRevoke}
                                    onAssignTools={() => setToolDialogGroupId(ga.group_id)}
                                />
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <AssignGroupDialog
                open={assignOpen}
                onOpenChange={setAssignOpen}
                groups={availableGroups}
                onConfirm={handleAssign}
            />

            {toolDialogGroupId && (
                <AssignToolDialog
                    open={!!toolDialogGroupId}
                    onOpenChange={(v) => { if (!v) setToolDialogGroupId(null); }}
                    groupId={toolDialogGroupId}
                    agentId={agentId}
                    orgId={orgId}
                    onSaved={() => setToolDialogGroupId(null)}
                />
            )}
        </>
    );
}

function GroupAccessItem({ item, onRevoke, onAssignTools }: {
    item: AgentGroupAccessItem;
    onRevoke: (groupId: string) => void;
    onAssignTools: () => void;
}) {
    const t = useTranslations("tenant");
    const { hasPermission } = usePermissions();

    return (
        <div className="flex items-center gap-3 rounded-lg border border-border/60 px-3 py-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium flex-1">{item.group_name}</span>
            <Button
                variant="ghost" size="sm"
                className="h-7 px-2 gap-1"
                onClick={onAssignTools}
                style={{ display: hasPermission("tool_access.assign") ? undefined : "none" }}
            >
                <Wrench className="h-3 w-3" /> {t("assignTools")}
            </Button>
            <Button
                variant="ghost" size="sm"
                className="text-destructive hover:text-destructive h-7 px-2"
                onClick={() => onRevoke(item.group_id)}
                style={{ display: hasPermission("agent.update") ? undefined : "none" }}
            >
                {t("remove")}
            </Button>
        </div>
    );
}

function AssignGroupDialog({ open, onOpenChange, groups, onConfirm }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    groups: Group[];
    onConfirm: (groupIds: string[]) => void;
}) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [search, setSearch] = useState("");

    const filteredGroups = groups.filter((g) =>
        g.name.toLowerCase().includes(search.toLowerCase())
    );

    const toggleGroup = (groupId: string) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(groupId)) {
                next.delete(groupId);
            } else {
                next.add(groupId);
            }
            return next;
        });
    };

    const toggleAll = () => {
        if (selectedIds.size === filteredGroups.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(filteredGroups.map((g) => g.id)));
        }
    };

    const handleConfirm = () => {
        onConfirm(Array.from(selectedIds));
        setSelectedIds(new Set());
        setSearch("");
    };

    const handleOpenChange = (v: boolean) => {
        if (!v) {
            setSelectedIds(new Set());
            setSearch("");
        }
        onOpenChange(v);
    };

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>{t("assignGroup")}</DialogTitle>
                    <DialogDescription>{t("assignGroupDesc")}</DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder={t("searchGroups")}
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-8 h-9"
                        />
                    </div>

                    {filteredGroups.length > 1 && (
                        <div className="flex items-center gap-2 px-1">
                            <Checkbox
                                id="select-all"
                                checked={selectedIds.size === filteredGroups.length && filteredGroups.length > 0}
                                onCheckedChange={toggleAll}
                            />
                            <Label htmlFor="select-all" className="text-xs text-muted-foreground cursor-pointer">
                                {t("selectAll")} ({filteredGroups.length})
                            </Label>
                        </div>
                    )}

                    <ScrollArea className="max-h-[240px]">
                        <div className="space-y-1">
                            {filteredGroups.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-4">{t("noGroupsFound")}</p>
                            ) : (
                                filteredGroups.map((g) => (
                                    <label
                                        key={g.id}
                                        className="flex items-center gap-3 rounded-md px-3 py-2 cursor-pointer hover:bg-muted/50 transition-colors"
                                    >
                                        <Checkbox
                                            checked={selectedIds.has(g.id)}
                                            onCheckedChange={() => toggleGroup(g.id)}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium truncate">{g.name}</div>
                                            {g.description && (
                                                <div className="text-xs text-muted-foreground truncate">{g.description}</div>
                                            )}
                                        </div>
                                    </label>
                                ))
                            )}
                        </div>
                    </ScrollArea>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => handleOpenChange(false)}>{tc("cancel")}</Button>
                    <Button onClick={handleConfirm} disabled={selectedIds.size === 0}>
                        {t("assignGroup")} {selectedIds.size > 0 && `(${selectedIds.size})`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
