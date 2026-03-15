"use client";

import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { toast } from "sonner";
import { usePermissions } from "@/hooks/use-permissions";

import { fetchFolderAccess, setFolderAccess, removeFolderAccess, fetchGroupsForAccess } from "@/lib/api/knowledge";
import type { FolderAccess } from "@/types/models";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Shield, Plus, Trash2, Lock, Globe, Search, Check } from "lucide-react";
import { PermissionGate } from "@/components/shared/permission-gate";
import { cn } from "@/lib/utils";

interface FolderAccessTabProps {
    folderId: string;
    accessType: string;
    onMutate?: () => void;
}

export function FolderAccessTab({ folderId, accessType, onMutate }: FolderAccessTabProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const { hasPermission } = usePermissions();
    const canEdit = hasPermission("folder_access.manage");

    const { data: accessList, mutate: mutateAccess } = useSWR(
        `folder-access-${folderId}`,
        () => fetchFolderAccess(folderId),
    );

    const { data: groups } = useSWR("folder-access-groups", fetchGroupsForAccess);

    // ── Multi-select combobox state ──
    const [selectedGroupIds, setSelectedGroupIds] = useState<Set<string>>(new Set());
    const [comboOpen, setComboOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [adding, setAdding] = useState(false);
    const comboRef = useRef<HTMLDivElement>(null);

    // Close combobox on click outside
    useEffect(() => {
        if (!comboOpen) return;
        const handler = (e: MouseEvent) => {
            if (comboRef.current && !comboRef.current.contains(e.target as Node)) {
                setComboOpen(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [comboOpen]);

    // Groups that already have access
    const assignedGroupIds = new Set((accessList || []).map((a: FolderAccess) => a.group_id));
    const availableGroups = useMemo(
        () => (groups || []).filter((g) => !assignedGroupIds.has(g.id)),
        [groups, assignedGroupIds],
    );

    const filteredGroups = useMemo(() => {
        if (!search.trim()) return availableGroups;
        const q = search.toLowerCase();
        return availableGroups.filter((g) => g.name.toLowerCase().includes(q));
    }, [availableGroups, search]);

    const toggleGroup = (groupId: string) => {
        setSelectedGroupIds((prev) => {
            const next = new Set(prev);
            if (next.has(groupId)) next.delete(groupId);
            else next.add(groupId);
            return next;
        });
    };

    const handleBatchAdd = useCallback(async () => {
        if (selectedGroupIds.size === 0) return;
        setAdding(true);
        try {
            await Promise.all(
                Array.from(selectedGroupIds).map((gid) =>
                    setFolderAccess(folderId, gid, true, false),
                ),
            );
            toast.success(t("accessGranted"));
            setSelectedGroupIds(new Set());
            setComboOpen(false);
            setSearch("");
            mutateAccess();
            onMutate?.();
        } catch {
            toast.error(tc("error"));
        } finally {
            setAdding(false);
        }
    }, [folderId, selectedGroupIds, mutateAccess, onMutate, t, tc]);

    const handleToggle = useCallback(async (
        groupId: string, field: "can_read" | "can_write",
        currentRead: boolean, currentWrite: boolean,
    ) => {
        try {
            const newRead = field === "can_read" ? !currentRead : currentRead;
            const newWrite = field === "can_write" ? !currentWrite : currentWrite;
            await setFolderAccess(folderId, groupId, newRead, newWrite);
            toast.success(tc("save"));
            mutateAccess();
            onMutate?.();
        } catch {
            toast.error(tc("error"));
        }
    }, [folderId, mutateAccess, onMutate, tc]);

    const handleRemove = useCallback(async (groupId: string) => {
        try {
            await removeFolderAccess(folderId, groupId);
            toast.success(t("accessRemoved"));
            mutateAccess();
            onMutate?.();
        } catch {
            toast.error(tc("error"));
        }
    }, [folderId, mutateAccess, onMutate, t, tc]);

    // Find group name by ID
    const groupName = (groupId: string) => {
        const fromAccess = accessList?.find((a: FolderAccess) => a.group_id === groupId);
        if (fromAccess?.group_name) return fromAccess.group_name;
        return groups?.find((g) => g.id === groupId)?.name ?? groupId;
    };

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <CardTitle className="text-sm">{t("folderAccess")}</CardTitle>
                </div>
                <CardDescription className="text-xs">
                    <Badge variant={accessType === "public" ? "default" : "secondary"} className="text-xs mr-2">
                        {accessType === "public" ? (
                            <><Globe className="h-3 w-3 mr-1" />{t("public")}</>
                        ) : (
                            <><Lock className="h-3 w-3 mr-1" />{t("restricted")}</>
                        )}
                    </Badge>
                    {accessType === "public" ? t("folderPublicDesc") : t("folderRestrictedDesc")}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* ── Multi-select combobox for adding groups ── */}
                {canEdit && availableGroups.length > 0 && (
                    <div className="flex items-start gap-2">
                        <div ref={comboRef} className="relative flex-1">
                            <button
                                type="button"
                                onClick={() => setComboOpen(!comboOpen)}
                                className={cn(
                                    "flex w-full items-center justify-between rounded-md border border-border/60 bg-transparent px-3 py-2 text-sm",
                                    "hover:bg-accent/50 transition-colors",
                                    comboOpen && "ring-1 ring-ring/30",
                                )}
                            >
                                <span className={cn(
                                    "truncate",
                                    selectedGroupIds.size === 0 && "text-muted-foreground",
                                )}>
                                    {selectedGroupIds.size > 0
                                        ? `${selectedGroupIds.size} ${t("groupsSelected")}`
                                        : t("selectGroup")
                                    }
                                </span>
                            </button>

                            {comboOpen && (
                                <div className="absolute z-50 mt-1 w-full rounded-md border border-border/60 bg-popover shadow-md animate-in fade-in-0 zoom-in-95">
                                    <div className="flex items-center gap-2 border-b border-border/40 px-3 py-2">
                                        <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                                        <input
                                            type="text"
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            placeholder={t("searchGroups")}
                                            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                                            autoFocus
                                        />
                                    </div>
                                    <div className="max-h-[200px] overflow-y-auto p-1">
                                        {filteredGroups.length === 0 ? (
                                            <p className="text-sm text-muted-foreground text-center py-4">
                                                {t("noGroupsFound")}
                                            </p>
                                        ) : (
                                            filteredGroups.map((g) => (
                                                <button
                                                    key={g.id}
                                                    type="button"
                                                    onClick={() => toggleGroup(g.id)}
                                                    className={cn(
                                                        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm cursor-pointer",
                                                        "hover:bg-accent hover:text-accent-foreground",
                                                        selectedGroupIds.has(g.id) && "bg-accent/50",
                                                    )}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "h-4 w-4 shrink-0",
                                                            selectedGroupIds.has(g.id) ? "opacity-100" : "opacity-0",
                                                        )}
                                                    />
                                                    <span className="flex-1 text-left truncate">{g.name}</span>
                                                </button>
                                            ))
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        <PermissionGate permission="folder_access.manage">
                            <Button
                                size="sm"
                                onClick={handleBatchAdd}
                                disabled={selectedGroupIds.size === 0 || adding}
                                className="gap-1 shrink-0"
                            >
                                <Plus className="h-3 w-3" />
                                {tc("add")}{selectedGroupIds.size > 0 && ` (${selectedGroupIds.size})`}
                            </Button>
                        </PermissionGate>
                    </div>
                )}

                {/* ── Access list with scroll ── */}
                {!accessList?.length ? (
                    <p className="text-sm text-muted-foreground text-center py-4">{t("noGroupAccess")}</p>
                ) : (
                    <ScrollArea className="max-h-[300px]">
                        <div className="space-y-2 pr-3">
                            {accessList.map((a: FolderAccess) => (
                                <div
                                    key={a.id}
                                    className="flex items-center justify-between rounded-md border px-3 py-2"
                                >
                                    <span className="text-sm font-medium truncate">{groupName(a.group_id)}</span>
                                    <div className="flex items-center gap-4 shrink-0">
                                        <div className="flex items-center gap-1.5">
                                            <Switch
                                                id={`read-${a.id}`}
                                                checked={a.can_read}
                                                onCheckedChange={() =>
                                                    handleToggle(a.group_id, "can_read", a.can_read, a.can_write)
                                                }
                                                disabled={!canEdit}
                                            />
                                            <Label htmlFor={`read-${a.id}`} className="text-xs">
                                                {t("canRead")}
                                            </Label>
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <Switch
                                                id={`write-${a.id}`}
                                                checked={a.can_write}
                                                onCheckedChange={() =>
                                                    handleToggle(a.group_id, "can_write", a.can_read, a.can_write)
                                                }
                                                disabled={!canEdit}
                                            />
                                            <Label htmlFor={`write-${a.id}`} className="text-xs">
                                                {t("canWrite")}
                                            </Label>
                                        </div>
                                        {canEdit && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 text-destructive hover:text-destructive"
                                                onClick={() => handleRemove(a.group_id)}
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                )}
            </CardContent>
        </Card>
    );
}
