"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { SystemProvider } from "@/types/models";
import {
  fetchSystemProviders,
  updateSystemProvider,
} from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
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
import { Switch } from "@/components/ui/switch";

export default function SystemProvidersPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<SystemProvider | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    api_base_url: "",
    auth_type: "api_key",
    is_active: true,
  });
  const [saving, setSaving] = useState(false);

  const { data, mutate, isLoading } = useSWR(
    "system-providers",
    fetchSystemProviders,
  );

  const columns: ColumnDef<SystemProvider, unknown>[] = [
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
    {
      accessorKey: "api_base_url",
      header: t("apiBaseUrl"),
      cell: ({ row }) => (
        <span className="text-muted-foreground text-xs">
          {row.original.api_base_url ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "auth_type",
      header: t("authType"),
      cell: ({ row }) => (
        <code className="text-xs">{row.original.auth_type}</code>
      ),
    },
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
          onEdit={() => {
            setEditingItem(row.original);
            setFormData({
              name: row.original.name,
              api_base_url: row.original.api_base_url ?? "",
              auth_type: row.original.auth_type,
              is_active: row.original.is_active,
            });
            setDialogOpen(true);
          }}
        />
      ),
    },
  ];

  const handleSave = useCallback(async () => {
    if (!editingItem) return;
    setSaving(true);
    try {
      await updateSystemProvider(editingItem.id, {
        name: formData.name,
        api_base_url: formData.api_base_url,
        auth_type: formData.auth_type,
        is_active: formData.is_active,
      });
      toast.success(t("updateSuccess"));
      setDialogOpen(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [editingItem, formData, mutate, t]);

  return (
    <div>
      <PageHeader title={ts("providersTitle")} description={ts("providersDesc")} />

      <DataTable
        columns={columns}
        data={data ?? []}
        total={data?.length ?? 0}
        page={1}
        pageSize={100}
        onPageChange={() => { }}
        isLoading={isLoading}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("edit")} {ts("provider")}
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
              <Label>{t("apiBaseUrl")}</Label>
              <Input
                value={formData.api_base_url}
                onChange={(e) =>
                  setFormData({ ...formData, api_base_url: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>{t("authType")}</Label>
              <Input
                value={formData.auth_type}
                onChange={(e) =>
                  setFormData({ ...formData, auth_type: e.target.value })
                }
              />
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={formData.is_active}
                onCheckedChange={(v) =>
                  setFormData({ ...formData, is_active: v })
                }
              />
              <Label>{t("active")}</Label>
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
    </div>
  );
}
