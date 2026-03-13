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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UserPlus, ShieldPlus, X } from "lucide-react";

export default function GroupDetailPage() {
    const t = useTranslations("common");
    const tg = useTranslations("tenant");
    const params = useParams();
    const groupId = params.groupId as string;
    const { orgId } = useCurrentOrg();
    const { hasPermission } = usePermissions();

    // Add member dialog
    const [addMemberOpen, setAddMemberOpen] = useState(false);
    const [selectedUserId, setSelectedUserId] = useState("");
    const [addingMember, setAddingMember] = useState(false);

    // Remove member
    const [removeMember, setRemoveMember] = useState<TenantUser | null>(null);

    // Assign permissions dialog
    const [assignOpen, setAssignOpen] = useState(false);
    const [selectedPermIds, setSelectedPermIds] = useState<string[]>([]);
    const [assigningPerms, setAssigningPerms] = useState(false);

    // Data fetching
    const { data: members, mutate: mutateMembers } = useSWR(
        groupId ? ["group-members", groupId] : null,
        () => fetchGroupMembers(groupId),
    );

    const { data: groupPerms, mutate: mutatePerms } = useSWR(
        groupId ? ["group-permissions", groupId] : null,
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
        if (!selectedUserId) return;
        setAddingMember(true);
        try {
            await addGroupMember(groupId, selectedUserId);
            toast.success(tg("memberAdded"));
            setAddMemberOpen(false);
            setSelectedUserId("");
            mutateMembers();
        } catch {
            toast.error(t("error"));
        } finally {
            setAddingMember(false);
        }
    }, [groupId, selectedUserId, mutateMembers, tg, t]);

    const handleRemoveMember = useCallback(async () => {
        if (!removeMember) return;
        try {
            await removeGroupMember(groupId, removeMember.user_id);
            toast.success(tg("memberRemoved"));
            setRemoveMember(null);
            mutateMembers();
        } catch {
            toast.error(t("error"));
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
        } catch {
            toast.error(t("error"));
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
            } catch {
                toast.error(t("error"));
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
            <Dialog open={addMemberOpen} onOpenChange={setAddMemberOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{tg("addMember")}</DialogTitle>
                        <DialogDescription>{tg("addMemberDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="py-2">
                        <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                            <SelectTrigger>
                                <SelectValue placeholder={tg("selectUser")} />
                            </SelectTrigger>
                            <SelectContent>
                                {availableUsers.map((u: TenantUser) => (
                                    <SelectItem key={u.user_id} value={u.user_id}>
                                        {u.full_name} ({u.email})
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAddMemberOpen(false)}>
                            {t("cancel")}
                        </Button>
                        <Button
                            onClick={handleAddMember}
                            disabled={addingMember || !selectedUserId}
                        >
                            {addingMember ? t("processing") : tg("addMember")}
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
