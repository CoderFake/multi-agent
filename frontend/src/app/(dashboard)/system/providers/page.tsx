"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { SystemProvider, AgentModel } from "@/types/models";
import {
  fetchSystemProviders,
  updateSystemProvider,
  fetchSystemModels,
  createSystemModel,
  updateSystemModel,
  deleteSystemModel,
} from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import {
  ChevronDown,
  Edit2,
  Plus,
  Trash2,
  Cpu,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function SystemProvidersPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const { data: providers, mutate, isLoading } = useSWR("system-providers", fetchSystemProviders);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // ── Provider Edit Dialog ────────────────────────────────────────────
  const [providerDialog, setProviderDialog] = useState(false);
  const [editingProvider, setEditingProvider] = useState<SystemProvider | null>(null);
  const [providerForm, setProviderForm] = useState({
    name: "", api_base_url: "", auth_type: "api_key", is_active: true,
  });
  const [saving, setSaving] = useState(false);

  const openProviderEdit = (p: SystemProvider) => {
    setEditingProvider(p);
    setProviderForm({
      name: p.name, api_base_url: p.api_base_url ?? "",
      auth_type: p.auth_type, is_active: p.is_active,
    });
    setProviderDialog(true);
  };

  const handleProviderSave = useCallback(async () => {
    if (!editingProvider) return;
    setSaving(true);
    try {
      await updateSystemProvider(editingProvider.id, providerForm);
      toast.success(t("updateSuccess"));
      setProviderDialog(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [editingProvider, providerForm, mutate, t]);

  if (isLoading) {
    return (
      <div>
        <PageHeader title={ts("providersTitle")} description={ts("providersDesc")} />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse"><CardContent className="p-6 h-28" /></Card>
          ))}
        </div>
      </div>
    );
  }

  const toggle = (id: string) => setExpandedId(expandedId === id ? null : id);

  return (
    <div className="space-y-6">
      <PageHeader title={ts("providersTitle")} description={ts("providersDesc")} />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(providers ?? []).map((provider) => (
          <ProviderCard
            key={provider.id}
            provider={provider}
            expanded={expandedId === provider.id}
            onToggle={() => toggle(provider.id)}
            onEdit={() => openProviderEdit(provider)}
            t={t}
          />
        ))}
      </div>

      {/* Provider Edit Dialog */}
      <Dialog open={providerDialog} onOpenChange={setProviderDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("edit")} {ts("provider")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t("name")}</Label>
              <Input value={providerForm.name} onChange={(e) => setProviderForm({ ...providerForm, name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("apiBaseUrl")}</Label>
              <Input value={providerForm.api_base_url} onChange={(e) => setProviderForm({ ...providerForm, api_base_url: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("authType")}</Label>
              <Input value={providerForm.auth_type} onChange={(e) => setProviderForm({ ...providerForm, auth_type: e.target.value })} />
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={providerForm.is_active} onCheckedChange={(v) => setProviderForm({ ...providerForm, is_active: v })} />
              <Label>{t("active")}</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setProviderDialog(false)}>{t("cancel")}</Button>
            <Button onClick={handleProviderSave} disabled={saving}>{saving ? t("processing") : t("save")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Provider Card ──────────────────────────────────────────────────────

function ProviderCard({
  provider, expanded, onToggle, onEdit, t,
}: {
  provider: SystemProvider;
  expanded: boolean;
  onToggle: () => void;
  onEdit: () => void;
  t: ReturnType<typeof useTranslations>;
}) {
  return (
    <Card
      className={cn(
        "transition-all cursor-pointer hover:border-primary/30",
        expanded && "border-primary/40 ring-1 ring-primary/10 col-span-1 md:col-span-2 lg:col-span-3",
      )}
      onClick={onToggle}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            {provider.name}
          </CardTitle>
          <div className="flex items-center gap-2">
            <StatusBadge status={provider.is_active} />
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={(e) => { e.stopPropagation(); onEdit(); }}>
              <Edit2 className="h-3.5 w-3.5" />
            </Button>
            <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", expanded && "rotate-180")} />
          </div>
        </div>
        <CardDescription className="text-xs">
          <code className="bg-muted px-1.5 py-0.5 rounded">{provider.slug}</code>
          {provider.api_base_url && <span className="ml-2 text-muted-foreground">{provider.api_base_url}</span>}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-xs text-muted-foreground">
          Auth: <code>{provider.auth_type}</code> · {formatDateTime(provider.created_at)}
        </div>

        {expanded && (
          <div className="mt-4 border-t pt-4" onClick={(e) => e.stopPropagation()}>
            <ModelList providerId={provider.id} t={t} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Model List + CRUD ──────────────────────────────────────────────────

function ModelList({ providerId, t }: { providerId: string; t: ReturnType<typeof useTranslations> }) {
  const { data: models, isLoading, mutate } = useSWR<AgentModel[]>(
    `sys-models-${providerId}`,
    () => fetchSystemModels(providerId),
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<AgentModel | null>(null);
  const [form, setForm] = useState({ name: "", model_type: "chat", context_window: "", pricing: "" });
  const [saving, setSaving] = useState(false);

  const openCreate = () => {
    setEditingModel(null);
    setForm({ name: "", model_type: "chat", context_window: "", pricing: "" });
    setDialogOpen(true);
  };

  const openEdit = (m: AgentModel) => {
    setEditingModel(m);
    setForm({
      name: m.name,
      model_type: m.model_type,
      context_window: m.context_window?.toString() ?? "",
      pricing: m.pricing_per_1m_tokens?.toString() ?? "",
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = {
        name: form.name,
        model_type: form.model_type,
        context_window: form.context_window ? parseInt(form.context_window) : null,
        pricing_per_1m_tokens: form.pricing ? parseFloat(form.pricing) : null,
      };
      if (editingModel) {
        await updateSystemModel(providerId, editingModel.id, data);
        toast.success(t("updateSuccess"));
      } else {
        await createSystemModel(providerId, data);
        toast.success(t("createSuccess"));
      }
      setDialogOpen(false);
      mutate();
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (model: AgentModel) => {
    if (!confirm(`Delete model "${model.name}"?`)) return;
    try {
      await deleteSystemModel(providerId, model.id);
      toast.success(t("deleteSuccess"));
      mutate();
    } catch {
      toast.error("Error");
    }
  };

  const handleToggleActive = async (model: AgentModel) => {
    try {
      await updateSystemModel(providerId, model.id, { is_active: !model.is_active });
      mutate();
    } catch {
      toast.error("Error");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-muted-foreground" />
          Models {models ? `(${models.length})` : ""}
        </h4>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={openCreate}>
          <Plus className="h-3 w-3 mr-1" /> Add Model
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <div key={i} className="h-8 animate-pulse rounded bg-muted" />)}
        </div>
      ) : !models?.length ? (
        <p className="text-xs text-muted-foreground py-4 text-center">No models configured</p>
      ) : (
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => (
            <div key={model.id} className="rounded-lg border bg-muted/20 px-3 py-2 flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{model.name}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <Badge variant="outline" className="text-[10px] h-4">{model.model_type}</Badge>
                  <StatusBadge status={model.is_active} />
                  {model.context_window && (
                    <span className="text-[10px] text-muted-foreground">{(model.context_window / 1000).toFixed(0)}k ctx</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Switch checked={model.is_active} onCheckedChange={() => handleToggleActive(model)} className="scale-75" />
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => openEdit(model)}>
                  <Edit2 className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => handleDelete(model)}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Model Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingModel ? t("edit") : t("create")} Model</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Model Name</Label>
              <Input placeholder="e.g. gpt-4o" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Input value={form.model_type} onChange={(e) => setForm({ ...form, model_type: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Context Window</Label>
                <Input type="number" placeholder="128000" value={form.context_window} onChange={(e) => setForm({ ...form, context_window: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Price/1M tokens</Label>
                <Input type="number" step="0.01" placeholder="2.50" value={form.pricing} onChange={(e) => setForm({ ...form, pricing: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>{t("cancel")}</Button>
            <Button onClick={handleSave} disabled={saving || !form.name.trim()}>
              {saving ? t("processing") : t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
