"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import type { TenantUser, TenantUserUpdate } from "@/types/models";
import { updateTenantUser, removeTenantUser } from "@/lib/api/tenant";
import { formatDateTime } from "@/lib/datetime";
import { usePermissions } from "@/hooks/use-permissions";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { SearchInput } from "@/components/shared/search-input";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ActionDropdown } from "@/components/shared/action-dropdown";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const ROLES = ["owner", "admin", "member"] as const;
const ROLE_LEVEL: Record<string, number> = { member: 1, admin: 2, owner: 3 };

interface UserMemberListProps {
    orgRole: string | null;
    data: { items: TenantUser[]; total: number } | undefined;
    page: number;
    onPageChange: (page: number) => void;
    search: string;
    onSearch: (q: string) => void;
    isLoading: boolean;
    onMutate: () => void;
}

export function UserMemberList({
    orgRole, data, page, onPageChange, search, onSearch, isLoading, onMutate,
}: UserMemberListProps) {
    const t = useTranslations("common");
    const tu = useTranslations("tenant");
    const { hasPermission } = usePermissions();
    const isSuperuser = orgRole === "superuser";
    const myLevel = isSuperuser ? 99 : (ROLE_LEVEL[orgRole ?? ""] ?? 0);

    // Edit role dialog
    const [editUser, setEditUser] = useState<TenantUser | null>(null);
    const [editRole, setEditRole] = useState<string>("member");
    const [saving, setSaving] = useState(false);

    // Remove dialog
    const [removeUser, setRemoveUser] = useState<TenantUser | null>(null);

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
                const targetLevel = ROLE_LEVEL[row.original.org_role] ?? 0;
                const canManage = isSuperuser || targetLevel < myLevel;
                if (!canManage) return null;

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

    // Edit role handler
    const handleEditRole = useCallback(async () => {
        if (!editUser) return;
        setSaving(true);
        try {
            await updateTenantUser(editUser.user_id, { org_role: editRole } as TenantUserUpdate);
            toast.success(t("updateSuccess"));
            setEditUser(null);
            onMutate();
        } catch {
            toast.error(t("error"));
        } finally {
            setSaving(false);
        }
    }, [editUser, editRole, onMutate, t]);

    // Remove handler
    const handleRemove = useCallback(async () => {
        if (!removeUser) return;
        try {
            await removeTenantUser(removeUser.user_id);
            toast.success(t("deleteSuccess"));
            setRemoveUser(null);
            onMutate();
        } catch {
            toast.error(t("error"));
        }
    }, [removeUser, onMutate, t]);

    return (
        <>
            <div className="mb-4">
                <SearchInput
                    onSearch={onSearch}
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
                onPageChange={onPageChange}
                isLoading={isLoading}
            />

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
                                    {ROLES.filter((r) => isSuperuser || ROLE_LEVEL[r] < myLevel).map((r) => (
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
        </>
    );
}
