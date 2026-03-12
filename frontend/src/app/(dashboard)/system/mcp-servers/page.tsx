"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { SystemMcpServer, McpServerCreateData, McpFormState } from "@/types/models";
import {
  fetchSystemMcpServers,
  createSystemMcpServer,
  updateSystemMcpServer,
  deleteSystemMcpServer,
} from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
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
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Plus } from "lucide-react";

const emptyForm: McpFormState = {
  codename: "",
  display_name: "",
  transport: "stdio",
  connection_config_json: "",
  is_active: true,
};

export default function SystemMcpServersPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<SystemMcpServer | null>(null);
  const [deleteItem, setDeleteItem] = useState<SystemMcpServer | null>(null);
  const [formData, setFormData] = useState<McpFormState>(emptyForm);
  const [saving, setSaving] = useState(false);

  const { data, mutate, isLoading } = useSWR(
    "system-mcp-servers",
    fetchSystemMcpServers,
  );

  /** Convert form state to API payload */
  const toPayload = (form: McpFormState): McpServerCreateData => ({
    codename: form.codename,
    display_name: form.display_name,
    transport: form.transport,
    connection_config: form.connection_config_json
      ? JSON.parse(form.connection_config_json)
      : null,
    is_active: form.is_active,
  });

  const columns: ColumnDef<SystemMcpServer, unknown>[] = [
    {
      accessorKey: "codename",
      header: t("codename"),
      cell: ({ row }) => (
        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
          {row.original.codename}
        </code>
      ),
    },
    {
      accessorKey: "display_name",
      header: t("displayName"),
      cell: ({ row }) => (
        <span className="font-medium">{row.original.display_name}</span>
      ),
    },
    {
      accessorKey: "transport",
      header: t("transport"),
      cell: ({ row }) => (
        <code className="text-xs">{row.original.transport}</code>
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
              codename: row.original.codename,
              display_name: row.original.display_name,
              transport: row.original.transport,
              connection_config_json: row.original.connection_config
                ? JSON.stringify(row.original.connection_config, null, 2)
                : "",
              is_active: row.original.is_active,
            });
            setDialogOpen(true);
          }}
          onDelete={() => setDeleteItem(row.original)}
        />
      ),
    },
  ];

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const payload = toPayload(formData);
      if (editingItem) {
        await updateSystemMcpServer(editingItem.id, {
          display_name: payload.display_name,
          transport: payload.transport,
          connection_config: payload.connection_config,
          is_active: payload.is_active,
        });
        toast.success(t("updateSuccess"));
      } else {
        await createSystemMcpServer(payload);
        toast.success(t("createSuccess"));
      }
      setDialogOpen(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [editingItem, formData, mutate, t]);

  const handleDelete = useCallback(async () => {
    if (!deleteItem) return;
    try {
      await deleteSystemMcpServer(deleteItem.id);
      toast.success(t("deleteSuccess"));
      setDeleteItem(null);
      mutate();
    } catch {
      toast.error("Error");
    }
  }, [deleteItem, mutate, t]);

  return (
    <div>
      <PageHeader title={ts("mcpTitle")} description={ts("mcpDesc")}>
        <Button
          onClick={() => {
            setEditingItem(null);
            setFormData(emptyForm);
            setDialogOpen(true);
          }}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          {ts("createMcp")}
        </Button>
      </PageHeader>

      <DataTable
        columns={columns}
        data={data ?? []}
        total={data?.length ?? 0}
        page={1}
        pageSize={100}
        onPageChange={() => {}}
        isLoading={isLoading}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingItem ? t("edit") : t("create")} {ts("mcpServer")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t("codename")}</Label>
              <Input
                value={formData.codename}
                onChange={(e) =>
                  setFormData({ ...formData, codename: e.target.value })
                }
                disabled={!!editingItem}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("displayName")}</Label>
              <Input
                value={formData.display_name}
                onChange={(e) =>
                  setFormData({ ...formData, display_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>{t("transport")}</Label>
              <Input
                value={formData.transport}
                onChange={(e) =>
                  setFormData({ ...formData, transport: e.target.value })
                }
                placeholder="stdio | sse | streamable_http"
              />
            </div>
            <div className="space-y-2">
              <Label>{ts("connectionConfig")}</Label>
              <Textarea
                value={formData.connection_config_json}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    connection_config_json: e.target.value,
                  })
                }
                rows={4}
                className="font-mono text-xs"
                placeholder='{"command": "npx", "args": [...]}'
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

      <ConfirmDialog
        open={!!deleteItem}
        onOpenChange={(o) => !o && setDeleteItem(null)}
        title={t("deleteConfirmTitle")}
        description={t("deleteConfirmDesc")}
        onConfirm={handleDelete}
      />
    </div>
  );
}
