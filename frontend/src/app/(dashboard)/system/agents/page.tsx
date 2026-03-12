"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import type { SystemAgent, AgentCreateData } from "@/types/models";
import {
  fetchSystemAgents,
  createSystemAgent,
  updateSystemAgent,
  deleteSystemAgent,
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

export default function SystemAgentsPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<SystemAgent | null>(null);
  const [deleteAgent, setDeleteAgent] = useState<SystemAgent | null>(null);
  const [formData, setFormData] = useState<AgentCreateData>({
    codename: "",
    display_name: "",
    description: "",
    is_active: true,
  });
  const [saving, setSaving] = useState(false);

  const { data, mutate, isLoading } = useSWR(
    "system-agents",
    fetchSystemAgents,
  );

  const columns: ColumnDef<SystemAgent, unknown>[] = [
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
      accessorKey: "description",
      header: t("description"),
      cell: ({ row }) => (
        <span className="text-muted-foreground truncate max-w-[200px] block">
          {row.original.description ?? "—"}
        </span>
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
          onEdit={() => openEdit(row.original)}
          onDelete={() => setDeleteAgent(row.original)}
        />
      ),
    },
  ];

  const openCreate = () => {
    setEditingAgent(null);
    setFormData({
      codename: "",
      display_name: "",
      description: "",
      is_active: true,
    });
    setDialogOpen(true);
  };

  const openEdit = (a: SystemAgent) => {
    setEditingAgent(a);
    setFormData({
      codename: a.codename,
      display_name: a.display_name,
      description: a.description ?? "",
      is_active: a.is_active,
    });
    setDialogOpen(true);
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      if (editingAgent) {
        await updateSystemAgent(editingAgent.id, {
          display_name: formData.display_name,
          description: formData.description,
          is_active: formData.is_active,
        });
        toast.success(t("updateSuccess"));
      } else {
        await createSystemAgent(formData);
        toast.success(t("createSuccess"));
      }
      setDialogOpen(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [editingAgent, formData, mutate, t]);

  const handleDelete = useCallback(async () => {
    if (!deleteAgent) return;
    try {
      await deleteSystemAgent(deleteAgent.id);
      toast.success(t("deleteSuccess"));
      setDeleteAgent(null);
      mutate();
    } catch {
      toast.error("Error");
    }
  }, [deleteAgent, mutate, t]);

  return (
    <div>
      <PageHeader title={ts("agentsTitle")} description={ts("agentsDesc")}>
        <Button onClick={openCreate} className="gap-2">
          <Plus className="h-4 w-4" />
          {ts("createAgent")}
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
              {editingAgent ? t("edit") : t("create")} {ts("agent")}
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
                disabled={!!editingAgent}
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
              <Label>{t("description")}</Label>
              <Textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows={3}
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
        open={!!deleteAgent}
        onOpenChange={(o) => !o && setDeleteAgent(null)}
        title={t("deleteConfirmTitle")}
        description={t("deleteConfirmDesc")}
        onConfirm={handleDelete}
      />
    </div>
  );
}
