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
  deleteSystemAgent,
} from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ActionDropdown } from "@/components/shared/action-dropdown";
import { AgentEditModal } from "@/components/agents/agent-edit-modal";
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
import { Plus, Globe } from "lucide-react";

export default function SystemAgentsPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [createOpen, setCreateOpen] = useState(false);
  const [editAgent, setEditAgent] = useState<SystemAgent | null>(null);
  const [deleteAgent, setDeleteAgent] = useState<SystemAgent | null>(null);
  const [formData, setFormData] = useState<AgentCreateData>({
    codename: "",
    display_name: "",
    description: "",
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
      accessorKey: "is_public",
      header: ts("isPublic"),
      cell: ({ row }) =>
        row.original.is_public ? (
          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
            <Globe className="h-3 w-3" />
            Public
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">Private</span>
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
          onEdit={() => setEditAgent(row.original)}
          onDelete={() => setDeleteAgent(row.original)}
        />
      ),
    },
  ];

  const handleCreate = useCallback(async () => {
    setSaving(true);
    try {
      await createSystemAgent(formData);
      toast.success(t("createSuccess"));
      setCreateOpen(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [formData, mutate, t]);

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
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
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

      {/* Create dialog — simple form */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("create")} {ts("agent")}
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving ? t("processing") : t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit modal — wide with org assignment + tools */}
      <AgentEditModal
        agent={editAgent}
        open={!!editAgent}
        onOpenChange={(open) => !open && setEditAgent(null)}
        onSaved={() => mutate()}
      />

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
