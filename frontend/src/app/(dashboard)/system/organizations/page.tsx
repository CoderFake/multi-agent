"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { OrganizationListItem, OrgCreateData } from "@/types/models";
import type { PaginatedResponse } from "@/types/api";
import {
  fetchOrganizations,
  createOrganization,
  updateOrganization,
  deleteOrganization,
} from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
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
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus } from "lucide-react";

export default function OrganizationsPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingOrg, setEditingOrg] = useState<OrganizationListItem | null>(
    null,
  );
  const [deleteOrg, setDeleteOrg] = useState<OrganizationListItem | null>(null);
  const [formData, setFormData] = useState<OrgCreateData>({
    name: "",
    slug: "",
    timezone: "UTC",
  });
  const [saving, setSaving] = useState(false);

  const { data, mutate, isLoading } = useSWR(
    ["system-organizations", page, search],
    () => fetchOrganizations({ page, pageSize: 20, search: search || undefined }),
  );

  const columns: ColumnDef<OrganizationListItem, unknown>[] = [
    {
      accessorKey: "name",
      header: t("name"),
      cell: ({ row }) => (
        <span className="font-medium">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "slug",
      header: t("slug"),
      cell: ({ row }) => (
        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
          {row.original.slug}
        </code>
      ),
    },
    { accessorKey: "member_count", header: t("members") },
    { accessorKey: "timezone", header: t("timezone") },
    {
      accessorKey: "is_active",
      header: t("status"),
      cell: ({ row }) => <StatusBadge status={row.original.is_active} />,
    },
    {
      accessorKey: "created_at",
      header: t("createdAt"),
      cell: ({ row }) => formatDateTime(row.original.created_at),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <ActionDropdown
          onEdit={() => openEdit(row.original)}
          onDelete={() => setDeleteOrg(row.original)}
        />
      ),
    },
  ];

  const openCreate = () => {
    setEditingOrg(null);
    setFormData({ name: "", slug: "", timezone: "UTC" });
    setDialogOpen(true);
  };

  const openEdit = (org: OrganizationListItem) => {
    setEditingOrg(org);
    setFormData({ name: org.name, slug: org.slug, timezone: org.timezone });
    setDialogOpen(true);
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      if (editingOrg) {
        await updateOrganization(editingOrg.id, formData);
        toast.success(t("updateSuccess"));
      } else {
        await createOrganization(formData);
        toast.success(t("createSuccess"));
      }
      setDialogOpen(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [editingOrg, formData, mutate, t]);

  const handleDelete = useCallback(async () => {
    if (!deleteOrg) return;
    try {
      await deleteOrganization(deleteOrg.id);
      toast.success(t("deleteSuccess"));
      setDeleteOrg(null);
      mutate();
    } catch {
      toast.error("Error");
    }
  }, [deleteOrg, mutate, t]);

  return (
    <div>
      <PageHeader title={ts("orgsTitle")} description={ts("orgsDesc")}>
        <Button onClick={openCreate} className="gap-2">
          <Plus className="h-4 w-4" />
          {ts("createOrg")}
        </Button>
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

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingOrg ? t("edit") : t("create")} {ts("orgsTitle")}
            </DialogTitle>
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
              <Label>{t("slug")}</Label>
              <Input
                value={formData.slug}
                onChange={(e) =>
                  setFormData({ ...formData, slug: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>{t("timezone")}</Label>
              <Input
                value={formData.timezone}
                onChange={(e) =>
                  setFormData({ ...formData, timezone: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? t("processing") : t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteOrg}
        onOpenChange={(open) => !open && setDeleteOrg(null)}
        title={t("deleteConfirmTitle")}
        description={t("deleteConfirmDesc")}
        onConfirm={handleDelete}
      />
    </div>
  );
}
