"use client";

import { useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { Group, GroupCreate } from "@/types/models";
import {
    fetchTenantGroups,
    createTenantGroup,
    updateTenantGroup,
    deleteTenantGroup,
} from "@/lib/api/tenant";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import { PageHeader } from "@/components/shared/page-header";
import { PermissionGate } from "@/components/shared/permission-gate";
import { DataTable } from "@/components/data-table/data-table";
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
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Plus } from "lucide-react";

export default function TenantGroupsPage() {
    const t = useTranslations("common");
    const tg = useTranslations("tenant");
    const router = useRouter();
    const params = useParams();
    const orgId = params.orgId as string;
    const { orgId: ctxOrgId } = useCurrentOrg();
    const { hasPermission } = usePermissions();

    // Dialog state
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editGroup, setEditGroup] = useState<Group | null>(null);
    const [deleteGroup, setDeleteGroup] = useState<Group | null>(null);
    const [formData, setFormData] = useState<GroupCreate>({ name: "", description: "" });
    const [saving, setSaving] = useState(false);

    const { data, mutate, isLoading } = useSWR(
        ctxOrgId ? ["tenant-groups", ctxOrgId] : null,
        () => fetchTenantGroups(),
    );

    const columns: ColumnDef<Group, unknown>[] = [
        {
            accessorKey: "name",
            header: t("name"),
            cell: ({ row }) => (
                <button
                    onClick={() => router.push(`/t/${orgId}/groups/${row.original.id}`)}
                    className="font-medium text-primary hover:underline text-left"
                >
                    {row.original.name}
                </button>
            ),
        },
        {
            accessorKey: "description",
            header: t("description"),
            cell: ({ row }) => (
                <span className="text-muted-foreground text-sm">
                    {row.original.description || "—"}
                </span>
            ),
        },
        {
            accessorKey: "is_system_default",
            header: tg("type"),
            cell: ({ row }) =>
                row.original.is_system_default ? (
                    <Badge variant="secondary">{tg("system")}</Badge>
                ) : (
                    <Badge variant="outline">{tg("custom")}</Badge>
                ),
        },
        {
            accessorKey: "member_count",
            header: t("members"),
        },
        {
            accessorKey: "permission_count",
            header: tg("permissions"),
        },
        {
            id: "actions",
            header: "",
            cell: ({ row }) => {
                if (row.original.is_system_default) return null;
                return (
                    <ActionDropdown
                        onEdit={
                            hasPermission("group.update")
                                ? () => {
                                    setEditGroup(row.original);
                                    setFormData({
                                        name: row.original.name,
                                        description: row.original.description || "",
                                    });
                                    setDialogOpen(true);
                                }
                                : undefined
                        }
                        onDelete={
                            hasPermission("group.delete")
                                ? () => setDeleteGroup(row.original)
                                : undefined
                        }
                    />
                );
            },
        },
    ];

    const openCreate = () => {
        setEditGroup(null);
        setFormData({ name: "", description: "" });
        setDialogOpen(true);
    };

    const handleSave = useCallback(async () => {
        setSaving(true);
        try {
            if (editGroup) {
                await updateTenantGroup(editGroup.id, formData);
                toast.success(t("updateSuccess"));
            } else {
                await createTenantGroup(formData);
                toast.success(t("createSuccess"));
            }
            setDialogOpen(false);
            mutate();
        } catch {
            toast.error(t("error"));
        } finally {
            setSaving(false);
        }
    }, [editGroup, formData, mutate, t]);

    const handleDelete = useCallback(async () => {
        if (!deleteGroup) return;
        try {
            await deleteTenantGroup(deleteGroup.id);
            toast.success(t("deleteSuccess"));
            setDeleteGroup(null);
            mutate();
        } catch {
            toast.error(t("error"));
        }
    }, [deleteGroup, mutate, t]);

    return (
        <PermissionGate permission="group.view" pageLevel>
            <div>
                <PageHeader title={tg("groupsTitle")} description={tg("groupsDesc")}>
                    {hasPermission("group.create") && (
                        <Button onClick={openCreate} className="gap-2">
                            <Plus className="h-4 w-4" />
                            {tg("createGroup")}
                        </Button>
                    )}
                </PageHeader>

                <DataTable
                    columns={columns}
                    data={data?.items ?? []}
                    total={data?.total ?? 0}
                    page={1}
                    pageSize={100}
                    onPageChange={() => { }}
                    isLoading={isLoading}
                />

                {/* Create/Edit Dialog */}
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>
                                {editGroup ? tg("editGroup") : tg("createGroup")}
                            </DialogTitle>
                            <DialogDescription>
                                {editGroup ? tg("editGroupDesc") : tg("createGroupDesc")}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-2">
                            <div className="space-y-2">
                                <Label>{t("name")}</Label>
                                <Input
                                    value={formData.name}
                                    onChange={(e) =>
                                        setFormData({ ...formData, name: e.target.value })
                                    }
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>{t("description")}</Label>
                                <Textarea
                                    value={formData.description || ""}
                                    onChange={(e) =>
                                        setFormData({ ...formData, description: e.target.value })
                                    }
                                    rows={3}
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setDialogOpen(false)}>
                                {t("cancel")}
                            </Button>
                            <Button onClick={handleSave} disabled={saving || !formData.name}>
                                {saving ? t("processing") : t("save")}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Delete Confirmation */}
                <ConfirmDialog
                    open={!!deleteGroup}
                    onOpenChange={(open) => !open && setDeleteGroup(null)}
                    title={t("deleteConfirmTitle")}
                    description={t("deleteConfirmDesc")}
                    onConfirm={handleDelete}
                />
            </div>
        </PermissionGate>
    );
}
