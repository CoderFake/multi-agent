"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { OrganizationListItem, OrgCreateData } from "@/types/models";
import {
  fetchOrganizations,
  createOrganization,
  deleteOrganization,
  fetchTimezones,
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
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteOrg, setDeleteOrg] = useState<OrganizationListItem | null>(null);
  const [formData, setFormData] = useState<OrgCreateData>({
    name: "",
    subdomain: "",
    timezone: "UTC",
  });
  const [saving, setSaving] = useState(false);

  const { data, mutate, isLoading } = useSWR(
    ["system-organizations", page, search],
    () => fetchOrganizations({ page, pageSize: 20, search: search || undefined }),
  );

  const { data: timezones } = useSWR("timezones", fetchTimezones);

  const columns: ColumnDef<OrganizationListItem, unknown>[] = [
    {
      accessorKey: "name",
      header: t("name"),
      cell: ({ row }) => (
        <button
          onClick={() => router.push(`/system/organizations/${row.original.id}`)}
          className="font-medium text-primary hover:underline text-left"
        >
          {row.original.name}
        </button>
      ),
    },
    {
      accessorKey: "subdomain",
      header: ts("subdomain"),
      cell: ({ row }) => (
        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
          {row.original.subdomain || row.original.slug}
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
          onEdit={() => router.push(`/system/organizations/${row.original.id}`)}
          onDelete={() => setDeleteOrg(row.original)}
        />
      ),
    },
  ];

  const openCreate = () => {
    setFormData({ name: "", subdomain: "", timezone: "UTC" });
    setDialogOpen(true);
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const org = await createOrganization(formData);
      toast.success(t("createSuccess"));
      setDialogOpen(false);
      mutate();
      // Redirect to detail page after create
      router.push(`/system/organizations/${org.id}`);
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      toast.error(detail || t("error"));
    } finally {
      setSaving(false);
    }
  }, [formData, mutate, t, router]);

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

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {ts("createOrg")}
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
              <Label>{ts("subdomain")} *</Label>
              <Input
                value={formData.subdomain}
                onChange={(e) =>
                  setFormData({ ...formData, subdomain: e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, "") })
                }
                placeholder="e.g. nws"
              />
              <p className="text-xs text-muted-foreground">
                Used as tenant identifier in production
              </p>
            </div>
            <div className="space-y-2">
              <Label>{t("timezone")}</Label>
              <select
                value={formData.timezone}
                onChange={(e) =>
                  setFormData({ ...formData, timezone: e.target.value })
                }
                className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-2 focus-visible:border-muted-foreground/70"
              >
                {(timezones ?? []).map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={handleSave} disabled={saving || !formData.name || !formData.subdomain}>
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
