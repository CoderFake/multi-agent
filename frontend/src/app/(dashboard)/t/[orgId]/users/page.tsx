"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { TenantUser, TenantUserUpdate } from "@/types/models";
import {
    fetchTenantUsers,
    updateTenantUser,
    removeTenantUser,
} from "@/lib/api/tenant";
import { createInvite } from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { SearchInput } from "@/components/shared/search-input";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ActionDropdown } from "@/components/shared/action-dropdown";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { UserPlus } from "lucide-react";

const ROLES = ["owner", "admin", "member"] as const;

export default function TenantUsersPage() {
    const t = useTranslations("common");
    const tu = useTranslations("tenant");
    const { orgId } = useCurrentOrg();
    const { hasPermission } = usePermissions();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");

    // Invite dialog
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteRole, setInviteRole] = useState<string>("member");
    const [inviting, setInviting] = useState(false);

    // Edit role dialog
    const [editUser, setEditUser] = useState<TenantUser | null>(null);
    const [editRole, setEditRole] = useState<string>("member");
    const [saving, setSaving] = useState(false);

    // Remove dialog
    const [removeUser, setRemoveUser] = useState<TenantUser | null>(null);

    const { data, mutate, isLoading } = useSWR(
        orgId ? ["tenant-users", orgId, page, search] : null,
        () => fetchTenantUsers({ page, pageSize: 20, search: search || undefined }),
    );

    const roleBadgeVariant = (role: string) => {
        if (role === "owner") return "default";
        if (role === "admin") return "secondary";
        return "outline";
    };

    const columns: ColumnDef<TenantUser, unknown>[] = [
        {
            accessorKey: "full_name",
            header: t("name"),
            cell: ({ row }) => (
                <div>
                    <span className="font-medium">{row.original.full_name}</span>
                    <p className="text-xs text-muted-foreground">{row.original.email}</p>
                </div>
            ),
        },
        {
            accessorKey: "org_role",
            header: tu("role"),
            cell: ({ row }) => (
                <Badge variant={roleBadgeVariant(row.original.org_role)}>
                    {row.original.org_role}
                </Badge>
            ),
        },
        {
            accessorKey: "is_active",
            header: t("status"),
            cell: ({ row }) => <StatusBadge status={row.original.is_active} />,
        },
        {
            accessorKey: "joined_at",
            header: tu("joinedAt"),
            cell: ({ row }) =>
                row.original.joined_at ? formatDateTime(row.original.joined_at) : "—",
        },
        {
            id: "actions",
            header: "",
            cell: ({ row }) => {
                const actions: { label: string; onClick: () => void; variant?: "destructive" }[] = [];
                if (hasPermission("user.update")) {
                    actions.push({
                        label: tu("editRole"),
                        onClick: () => {
                            setEditUser(row.original);
                            setEditRole(row.original.org_role);
                        },
                    });
                }
                if (hasPermission("user.delete")) {
                    actions.push({
                        label: t("delete"),
                        onClick: () => setRemoveUser(row.original),
                        variant: "destructive",
                    });
                }
                if (actions.length === 0) return null;
                return (
                    <ActionDropdown
                        onEdit={
                            hasPermission("user.update")
                                ? () => {
                                    setEditUser(row.original);
                                    setEditRole(row.original.org_role);
                                }
                                : undefined
                        }
                        onDelete={
                            hasPermission("user.delete")
                                ? () => setRemoveUser(row.original)
                                : undefined
                        }
                    />
                );
            },
        },
    ];

    // Invite handler
    const handleInvite = useCallback(async () => {
        if (!orgId) return;
        setInviting(true);
        try {
            await createInvite({ email: inviteEmail, org_id: orgId, org_role: inviteRole });
            toast.success(tu("inviteSent"));
            setInviteOpen(false);
            setInviteEmail("");
            setInviteRole("member");
            mutate();
        } catch {
            toast.error(t("error"));
        } finally {
            setInviting(false);
        }
    }, [orgId, inviteEmail, inviteRole, mutate, tu, t]);

    // Edit role handler
    const handleEditRole = useCallback(async () => {
        if (!editUser) return;
        setSaving(true);
        try {
            await updateTenantUser(editUser.user_id, { org_role: editRole } as TenantUserUpdate);
            toast.success(t("updateSuccess"));
            setEditUser(null);
            mutate();
        } catch {
            toast.error(t("error"));
        } finally {
            setSaving(false);
        }
    }, [editUser, editRole, mutate, t]);

    // Remove handler
    const handleRemove = useCallback(async () => {
        if (!removeUser) return;
        try {
            await removeTenantUser(removeUser.user_id);
            toast.success(t("deleteSuccess"));
            setRemoveUser(null);
            mutate();
        } catch {
            toast.error(t("error"));
        }
    }, [removeUser, mutate, t]);

    return (
        <div>
            <PageHeader title={tu("usersTitle")} description={tu("usersDesc")}>
                {hasPermission("user.create") && (
                    <Button onClick={() => setInviteOpen(true)} className="gap-2">
                        <UserPlus className="h-4 w-4" />
                        {tu("inviteUser")}
                    </Button>
                )}
            </PageHeader>

            <div className="mb-4">
                <SearchInput
                    onSearch={setSearch}
                    placeholder={t("search")}
                    className="max-w-sm"
                />
            </div>

            <DataTable
                columns={columns}
                data={data?.items ?? []}
                total={data?.total ?? 0}
                page={page}
                pageSize={20}
                onPageChange={setPage}
                isLoading={isLoading}
            />

            {/* Invite Dialog */}
            <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{tu("inviteUser")}</DialogTitle>
                        <DialogDescription>{tu("inviteUserDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label>{t("email")}</Label>
                            <Input
                                type="email"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                                placeholder="user@example.com"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>{tu("role")}</Label>
                            <Select value={inviteRole} onValueChange={setInviteRole}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ROLES.map((r) => (
                                        <SelectItem key={r} value={r}>
                                            {r}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setInviteOpen(false)}>
                            {t("cancel")}
                        </Button>
                        <Button onClick={handleInvite} disabled={inviting || !inviteEmail}>
                            {inviting ? t("processing") : tu("sendInvite")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Edit Role Dialog */}
            <Dialog open={!!editUser} onOpenChange={(open) => !open && setEditUser(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{tu("editRole")}</DialogTitle>
                        <DialogDescription>
                            {editUser?.full_name} ({editUser?.email})
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label>{tu("role")}</Label>
                            <Select value={editRole} onValueChange={setEditRole}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ROLES.map((r) => (
                                        <SelectItem key={r} value={r}>
                                            {r}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditUser(null)}>
                            {t("cancel")}
                        </Button>
                        <Button onClick={handleEditRole} disabled={saving}>
                            {saving ? t("processing") : t("save")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Remove Confirmation */}
            <ConfirmDialog
                open={!!removeUser}
                onOpenChange={(open) => !open && setRemoveUser(null)}
                title={tu("removeMemberTitle")}
                description={tu("removeMemberDesc")}
                onConfirm={handleRemove}
            />
        </div>
    );
}
