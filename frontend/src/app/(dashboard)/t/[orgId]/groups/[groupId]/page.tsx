"use client";

import { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { TenantUser, Permission } from "@/types/models";
import {
    fetchGroupMembers,
    fetchGroupPermissions,
    addGroupMember,
    removeGroupMember,
    assignGroupPermissions,
    revokeGroupPermissions,
    fetchTenantUsers,
    fetchTenantPermissions,
} from "@/lib/api/tenant";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import { useErrorToast } from "@/hooks/use-error-toast";
import { PageHeader } from "@/components/shared/page-header";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UserPlus, ShieldPlus, X, Search } from "lucide-react";

export default function GroupDetailPage() {
    const t = useTranslations("common");
    const tg = useTranslations("tenant");
    const params = useParams();
    const groupId = params.groupId as string;
    const { orgId } = useCurrentOrg();
    const { hasPermission } = usePermissions();
    const { showError } = useErrorToast();

    // Add member dialog
    const [addMemberOpen, setAddMemberOpen] = useState(false);
    const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());
    const [addingMember, setAddingMember] = useState(false);
    const [memberSearch, setMemberSearch] = useState("");

    // Remove member
    const [removeMember, setRemoveMember] = useState<TenantUser | null>(null);

    // Assign permissions dialog
    const [assignOpen, setAssignOpen] = useState(false);
    const [selectedPermIds, setSelectedPermIds] = useState<string[]>([]);
    const [assigningPerms, setAssigningPerms] = useState(false);

    // Data fetching
    const { data: members, mutate: mutateMembers } = useSWR(
        orgId && groupId ? ["group-members", orgId, groupId] : null,
        () => fetchGroupMembers(groupId),
    );

    const { data: groupPerms, mutate: mutatePerms } = useSWR(
        orgId && groupId ? ["group-permissions", orgId, groupId] : null,
        () => fetchGroupPermissions(groupId),
    );

    const { data: allUsersData } = useSWR(
        addMemberOpen && orgId ? ["tenant-users-all", orgId] : null,
        () => fetchTenantUsers({ page: 1, pageSize: 100 }),
    );

    const { data: allPerms } = useSWR(
        assignOpen && orgId ? ["all-permissions", orgId] : null,
        () => fetchTenantPermissions(),
    );

    // Filter users not already in group
    const memberIds = new Set((members ?? []).map((m: TenantUser) => m.user_id));
    const availableUsers = (allUsersData?.items ?? []).filter(
        (u: TenantUser) => !memberIds.has(u.user_id),
    );

    // Filter permissions not already assigned
    const assignedPermIds = new Set((groupPerms ?? []).map((p: Permission) => p.id));
    const availablePerms = (allPerms ?? []).filter(
        (p: Permission) => !assignedPermIds.has(p.id),
    );

    // Handlers
    const handleAddMember = useCallback(async () => {
        if (selectedUserIds.size === 0) return;
        setAddingMember(true);
        try {
            await addGroupMember(groupId, Array.from(selectedUserIds));
            toast.success(tg("memberAdded"));
            setAddMemberOpen(false);
            setSelectedUserIds(new Set());
            setMemberSearch("");
            mutateMembers();
        } catch (err) {
            showError(err);
        } finally {
            setAddingMember(false);
        }
    }, [groupId, selectedUserIds, mutateMembers, tg, t]);

    const handleRemoveMember = useCallback(async () => {
        if (!removeMember) return;
        try {
            await removeGroupMember(groupId, removeMember.user_id);
            toast.success(tg("memberRemoved"));
            setRemoveMember(null);
            mutateMembers();
        } catch (err) {
            showError(err);
        }
    }, [groupId, removeMember, mutateMembers, tg, t]);

    const handleAssignPerms = useCallback(async () => {
        if (selectedPermIds.length === 0) return;
        setAssigningPerms(true);
        try {
            await assignGroupPermissions(groupId, selectedPermIds);
            toast.success(tg("permissionsAssigned"));
            setAssignOpen(false);
            setSelectedPermIds([]);
            mutatePerms();
        } catch (err) {
            showError(err);
        } finally {
            setAssigningPerms(false);
        }
    }, [groupId, selectedPermIds, mutatePerms, tg, t]);

    const handleRevokePermission = useCallback(
        async (permId: string) => {
            try {
                await revokeGroupPermissions(groupId, [permId]);
                toast.success(tg("permissionRevoked"));
                mutatePerms();
            } catch (err) {
                showError(err);
            }
        },
        [groupId, mutatePerms, tg, t],
    );

    const togglePermSelection = (permId: string) => {
        setSelectedPermIds((prev) =>
            prev.includes(permId) ? prev.filter((id) => id !== permId) : [...prev, permId],
        );
    };

    return (
        <div>
            <PageHeader title={tg("groupDetail")} description={tg("groupDetailDesc")} />

            <Tabs defaultValue="members" className="mt-4">
                <TabsList>
                    <TabsTrigger value="members">
                        {t("members")} ({(members ?? []).length})
                    </TabsTrigger>
                    <TabsTrigger value="permissions">
                        {tg("permissions")} ({(groupPerms ?? []).length})
                    </TabsTrigger>
                </TabsList>

                {/* Members Tab */}
                <TabsContent value="members">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-lg">{t("members")}</CardTitle>
                                <CardDescription>{tg("groupMembersDesc")}</CardDescription>
                            </div>
                            {hasPermission("group.update") && (
                                <Button
                                    size="sm"
                                    onClick={() => setAddMemberOpen(true)}
                                    className="gap-2"
                                >
                                    <UserPlus className="h-4 w-4" />
                                    {tg("addMember")}
                                </Button>
                            )}
                        </CardHeader>
                        <CardContent>
                            {(members ?? []).length === 0 ? (
                                <p className="text-sm text-muted-foreground py-4 text-center">
                                    {tg("noMembers")}
                                </p>
                            ) : (
                                <div className="space-y-2">
                                    {(members ?? []).map((user: TenantUser) => (
                                        <div
                                            key={user.user_id}
                                            className="flex items-center justify-between rounded-lg border p-3"
                                        >
                                            <div>
                                                <span className="font-medium text-sm">{user.full_name}</span>
                                                <p className="text-xs text-muted-foreground">{user.email}</p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge variant="outline">{user.org_role}</Badge>
                                                {hasPermission("group.update") && (
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                                        onClick={() => setRemoveMember(user)}
                                                    >
                                                        <X className="h-4 w-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Permissions Tab */}
                <TabsContent value="permissions">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-lg">{tg("permissions")}</CardTitle>
                                <CardDescription>{tg("groupPermissionsDesc")}</CardDescription>
                            </div>
                            {hasPermission("group.update") && (
                                <Button
                                    size="sm"
                                    onClick={() => {
                                        setSelectedPermIds([]);
                                        setAssignOpen(true);
                                    }}
                                    className="gap-2"
                                >
                                    <ShieldPlus className="h-4 w-4" />
                                    {tg("assignPermissions")}
                                </Button>
                            )}
                        </CardHeader>
                        <CardContent>
                            {(groupPerms ?? []).length === 0 ? (
                                <p className="text-sm text-muted-foreground py-4 text-center">
                                    {tg("noPermissions")}
                                </p>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {(groupPerms ?? []).map((perm: Permission) => (
                                        <Badge
                                            key={perm.id}
                                            variant="secondary"
                                            className="gap-1 pr-1 cursor-default"
                                        >
                                            <span>{perm.codename}</span>
                                            {hasPermission("group.update") && (
                                                <button
                                                    onClick={() => handleRevokePermission(perm.id)}
                                                    className="ml-1 rounded-sm hover:bg-destructive/20 p-0.5"
                                                >
                                                    <X className="h-3 w-3" />
                                                </button>
                                            )}
                                        </Badge>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Add Member Dialog */}
            <Dialog open={addMemberOpen} onOpenChange={(v) => {
                setAddMemberOpen(v);
                if (!v) { setSelectedUserIds(new Set()); setMemberSearch(""); }
            }}>
                <DialogContent className="max-w-lg flex flex-col max-h-[80vh]">
                    <DialogHeader>
                        <DialogTitle>{tg("addMember")}</DialogTitle>
                        <DialogDescription>{tg("addMemberDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder={t("search")}
                            value={memberSearch}
                            onChange={(e) => setMemberSearch(e.target.value)}
                            className="pl-8 h-9"
                        />
                    </div>
                    <ScrollArea className="h-[400px] -mx-6 px-6">
                        {(() => {
                            const filtered = availableUsers.filter((u: TenantUser) =>
                                u.full_name.toLowerCase().includes(memberSearch.toLowerCase()) ||
                                u.email.toLowerCase().includes(memberSearch.toLowerCase())
                            );
                            if (filtered.length === 0) {
                                return (
                                    <p className="text-sm text-muted-foreground text-center py-8">
                                        {tg("noUsersFound")}
                                    </p>
                                );
                            }
                            return (
                                <div className="space-y-1 py-1">
                                    {filtered.length > 1 && (
                                        <label className="flex items-center gap-3 rounded-md px-3 py-2 cursor-pointer hover:bg-muted/50 border-b border-border/40 mb-1">
                                            <Checkbox
                                                checked={filtered.every((u: TenantUser) => selectedUserIds.has(u.user_id))}
                                                onCheckedChange={() => {
                                                    const allSelected = filtered.every((u: TenantUser) => selectedUserIds.has(u.user_id));
                                                    setSelectedUserIds((prev) => {
                                                        const next = new Set(prev);
                                                        filtered.forEach((u: TenantUser) => {
                                                            if (allSelected) next.delete(u.user_id);
                                                            else next.add(u.user_id);
                                                        });
                                                        return next;
                                                    });
                                                }}
                                            />
                                            <span className="text-xs text-muted-foreground">{t("selectAll")} ({filtered.length})</span>
                                        </label>
                                    )}
                                    {filtered.map((u: TenantUser) => (
                                        <label
                                            key={u.user_id}
                                            className="flex items-center gap-3 rounded-md px-3 py-2 cursor-pointer hover:bg-muted/50 transition-colors"
                                        >
                                            <Checkbox
                                                checked={selectedUserIds.has(u.user_id)}
                                                onCheckedChange={() => {
                                                    setSelectedUserIds((prev) => {
                                                        const next = new Set(prev);
                                                        if (next.has(u.user_id)) next.delete(u.user_id);
                                                        else next.add(u.user_id);
                                                        return next;
                                                    });
                                                }}
                                            />
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-medium truncate">{u.full_name}</div>
                                                <div className="text-xs text-muted-foreground truncate">{u.email}</div>
                                            </div>
                                            <Badge variant="outline" className="text-[10px] shrink-0">{u.org_role}</Badge>
                                        </label>
                                    ))}
                                </div>
                            );
                        })()}
                    </ScrollArea>
                    <DialogFooter className="pt-3 border-t border-border/40">
                        <Button variant="outline" onClick={() => setAddMemberOpen(false)}>
                            {t("cancel")}
                        </Button>
                        <Button
                            onClick={handleAddMember}
                            disabled={addingMember || selectedUserIds.size === 0}
                        >
                            {addingMember ? t("processing") : `${tg("addMember")} (${selectedUserIds.size})`}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Assign Permissions Dialog — grouped by resource */}
            <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
                <DialogContent className="max-w-lg flex flex-col max-h-[80vh]">
                    <DialogHeader>
                        <DialogTitle>{tg("assignPermissions")}</DialogTitle>
                        <DialogDescription>{tg("assignPermissionsDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="flex-1 overflow-y-auto min-h-0 -mx-6 px-6">
                        {availablePerms.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-8">
                                {tg("allPermissionsAssigned")}
                            </p>
                        ) : (
                            <div className="space-y-4 py-2">
                                {(() => {
                                    // Group available perms by resource
                                    const grouped: Record<string, Permission[]> = {};
                                    availablePerms.forEach((p: Permission) => {
                                        const resource = p.codename.split(".")[0] || "other";
                                        if (!grouped[resource]) grouped[resource] = [];
                                        grouped[resource].push(p);
                                    });

                                    const RESOURCE_LABELS: Record<string, string> = {
                                        user: "User", organization: "Organization", group: "Group",
                                        permission: "Permission", invite: "Invite", agent: "Agent",
                                        mcp_server: "MCP Server", agent_mcp: "Agent MCP",
                                        tool: "Tool", tool_access: "Tool Access", ui_component: "UI Component",
                                        provider: "Provider", provider_key: "Provider Key",
                                        folder: "Folder", document: "Document",
                                        system_setting: "System Setting", audit_log: "Audit Log",
                                        feedback: "Feedback", notification: "Notification",
                                    };

                                    return Object.entries(grouped).map(([resource, perms]) => {
                                        const allSelected = perms.every((p) => selectedPermIds.includes(p.id));
                                        const someSelected = perms.some((p) => selectedPermIds.includes(p.id));

                                        const toggleAll = () => {
                                            if (allSelected) {
                                                setSelectedPermIds((prev) =>
                                                    prev.filter((id) => !perms.some((p) => p.id === id)),
                                                );
                                            } else {
                                                setSelectedPermIds((prev) => [
                                                    ...prev,
                                                    ...perms.filter((p) => !prev.includes(p.id)).map((p) => p.id),
                                                ]);
                                            }
                                        };

                                        return (
                                            <div key={resource} className="rounded-lg border border-border/60">
                                                <label
                                                    className="flex items-center gap-3 px-3 py-2 bg-muted/50 cursor-pointer hover:bg-muted rounded-t-lg border-b border-border/40"
                                                    onClick={toggleAll}
                                                >
                                                    <Checkbox
                                                        checked={allSelected ? true : someSelected ? "indeterminate" : false}
                                                        onCheckedChange={toggleAll}
                                                    />
                                                    <span className="text-sm font-semibold">
                                                        {RESOURCE_LABELS[resource] ?? resource}
                                                    </span>
                                                    <span className="text-xs text-muted-foreground ml-auto">
                                                        {perms.filter((p) => selectedPermIds.includes(p.id)).length}/{perms.length}
                                                    </span>
                                                </label>
                                                <div className="p-2 space-y-0.5">
                                                    {perms.map((perm) => {
                                                        const action = perm.codename.split(".")[1] ?? "";
                                                        return (
                                                            <label
                                                                key={perm.id}
                                                                className="flex items-center gap-3 rounded px-2 py-1.5 cursor-pointer hover:bg-muted/50"
                                                            >
                                                                <Checkbox
                                                                    checked={selectedPermIds.includes(perm.id)}
                                                                    onCheckedChange={() => togglePermSelection(perm.id)}
                                                                />
                                                                <span className="text-sm">{action}</span>
                                                                <span className="text-xs text-muted-foreground ml-auto">
                                                                    {perm.name}
                                                                </span>
                                                            </label>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        );
                                    });
                                })()}
                            </div>
                        )}
                    </div>
                    <DialogFooter className="pt-3 border-t border-border/40">
                        <Button variant="outline" onClick={() => setAssignOpen(false)}>
                            {t("cancel")}
                        </Button>
                        <Button
                            onClick={handleAssignPerms}
                            disabled={assigningPerms || selectedPermIds.length === 0}
                        >
                            {assigningPerms
                                ? t("processing")
                                : `${tg("assign")} (${selectedPermIds.length})`}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Remove Member Confirmation */}
            <ConfirmDialog
                open={!!removeMember}
                onOpenChange={(open) => !open && setRemoveMember(null)}
                title={tg("removeMemberTitle")}
                description={tg("removeMemberDesc")}
                onConfirm={handleRemoveMember}
            />
        </div>
    );
}
