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
import { Combobox } from "@/components/ui/combobox";
import { Users } from "lucide-react";

interface AgentGroupAccessItem extends GroupAgent {
    group_name: string;
}

interface AgentGroupAccessProps {
    agentGroups: AgentGroupAccessItem[];
    groups: Group[];
    onAssign: (groupId: string) => void;
    onRevoke: (groupId: string) => void;
}

export function AgentGroupAccess({ agentGroups, groups, onAssign, onRevoke }: AgentGroupAccessProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [assignOpen, setAssignOpen] = useState(false);
    const [selectedGroupId, setSelectedGroupId] = useState("");

    const handleAssign = () => {
        if (!selectedGroupId) return;
        onAssign(selectedGroupId);
        setAssignOpen(false);
        setSelectedGroupId("");
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
                        <Button size="sm" variant="outline" onClick={() => setAssignOpen(true)} className="gap-1.5">
                            <Users className="h-3.5 w-3.5" /> {t("assignGroup")}
                        </Button>
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
                                <GroupAccessItem key={ga.id} item={ga} onRevoke={onRevoke} />
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <AssignGroupDialog
                open={assignOpen}
                onOpenChange={setAssignOpen}
                groups={groups}
                selectedGroupId={selectedGroupId}
                onGroupChange={setSelectedGroupId}
                onConfirm={handleAssign}
            />
        </>
    );
}

function GroupAccessItem({ item, onRevoke }: { item: AgentGroupAccessItem; onRevoke: (groupId: string) => void }) {
    const t = useTranslations("tenant");

    return (
        <div className="flex items-center gap-3 rounded-lg border border-border/60 px-3 py-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium flex-1">{item.group_name}</span>
            <Button
                variant="ghost" size="sm"
                className="text-destructive hover:text-destructive h-7 px-2"
                onClick={() => onRevoke(item.group_id)}
            >
                {t("remove")}
            </Button>
        </div>
    );
}

function AssignGroupDialog({ open, onOpenChange, groups, selectedGroupId, onGroupChange, onConfirm }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    groups: Group[];
    selectedGroupId: string;
    onGroupChange: (v: string) => void;
    onConfirm: () => void;
}) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-sm">
                <DialogHeader>
                    <DialogTitle>{t("assignGroup")}</DialogTitle>
                    <DialogDescription>{t("assignGroupDesc")}</DialogDescription>
                </DialogHeader>
                <div className="space-y-2">
                    <Label className="text-xs">{t("groupAccess")}</Label>
                    <Combobox
                        options={groups.map((g) => ({
                            value: g.id,
                            label: g.name,
                            description: g.description ?? undefined,
                        }))}
                        value={selectedGroupId}
                        onValueChange={onGroupChange}
                        placeholder={t("selectGroup")}
                        searchPlaceholder={t("searchGroups")}
                        emptyText={t("noGroupsFound")}
                    />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>{tc("cancel")}</Button>
                    <Button onClick={onConfirm} disabled={!selectedGroupId}>{t("assignGroup")}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
