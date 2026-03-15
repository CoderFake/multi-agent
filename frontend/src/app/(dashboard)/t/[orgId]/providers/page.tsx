"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import useSWR, { useSWRConfig } from "swr";
import { toast } from "sonner";
import { usePermissions } from "@/hooks/use-permissions";
import { PageHeader } from "@/components/shared/page-header";
import { PermissionGate } from "@/components/shared/permission-gate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
    DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Plug, Key, Plus, Trash2, Eye, EyeOff } from "lucide-react";
import {
    fetchTenantProviders, fetchProviderKeys, fetchProviderModels,
    addProviderKey, updateProviderKey, deleteProviderKey,
} from "@/lib/api/tenant-providers";
import type { SystemProvider, ProviderKey, AgentModel } from "@/types/models";

export default function TenantProvidersPage() {
    const t = useTranslations("tenant");
    const [selectedProvider, setSelectedProvider] = useState<SystemProvider | null>(null);

    return (
        <PermissionGate permission="provider.view" pageLevel>
            <div className="space-y-6">
                <PageHeader title={t("tenantProvidersTitle")} description={t("tenantProvidersDesc")} />
                {selectedProvider ? (
                    <ProviderKeyManager
                        provider={selectedProvider}
                        onBack={() => setSelectedProvider(null)}
                    />
                ) : (
                    <ProvidersList onSelect={setSelectedProvider} />
                )}
            </div>
        </PermissionGate>
    );
}

function ProvidersList({ onSelect }: { onSelect: (p: SystemProvider) => void }) {
    const t = useTranslations("tenant");
    const { data: providers, isLoading } = useSWR("tenant-providers", fetchTenantProviders);

    if (isLoading) {
        return (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3].map((i) => (
                    <Card key={i} className="animate-pulse">
                        <CardContent className="p-6 h-32" />
                    </Card>
                ))}
            </div>
        );
    }

    if (!providers?.length) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
                    <Plug className="h-12 w-12 text-muted-foreground/50" />
                    <p className="text-muted-foreground">{t("noProviders")}</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {providers.map((provider) => (
                <ProviderCard key={provider.id} provider={provider} onSelect={onSelect} />
            ))}
        </div>
    );
}

function ProviderCard({ provider, onSelect }: { provider: SystemProvider; onSelect: (p: SystemProvider) => void }) {
    const t = useTranslations("tenant");
    const { data: models } = useSWR(
        `provider-models-${provider.id}`,
        () => fetchProviderModels(provider.id),
    );
    const chatModels = (models ?? []).filter((m) => m.model_type === "chat");
    const embeddingModels = (models ?? []).filter((m) => m.model_type === "embedding");

    return (
        <Card
            className="cursor-pointer hover:border-primary/30 transition-colors"
            onClick={() => onSelect(provider)}
        >
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Plug className="h-4 w-4 text-primary" />
                        {provider.name}
                    </CardTitle>
                    <Badge variant={provider.is_active ? "default" : "secondary"}>
                        {provider.is_active ? t("active") : t("inactive")}
                    </Badge>
                </div>
                <CardDescription className="text-xs font-mono">{provider.slug}</CardDescription>
            </CardHeader>
            <CardContent className="pt-0 space-y-2">
                {chatModels.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {chatModels.map((m) => (
                            <Badge key={m.id} variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
                                {m.name}
                            </Badge>
                        ))}
                    </div>
                )}
                {embeddingModels.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {embeddingModels.map((m) => (
                            <Badge key={m.id} variant="secondary" className="text-[10px] px-1.5 py-0 font-mono">
                                📐 {m.name}
                            </Badge>
                        ))}
                    </div>
                )}
                <div className="flex items-center gap-2 text-sm text-muted-foreground pt-1">
                    <Key className="h-3.5 w-3.5" />
                    <span>{t("manageKeys")}</span>
                </div>
            </CardContent>
        </Card>
    );
}

function ProviderKeyManager({
    provider,
    onBack,
}: {
    provider: SystemProvider;
    onBack: () => void;
}) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const { hasPermission } = usePermissions();
    const { mutate: globalMutate } = useSWRConfig();
    const { data: keys, mutate } = useSWR(
        `provider-keys-${provider.id}`,
        () => fetchProviderKeys(provider.id)
    );
    const [addDialogOpen, setAddDialogOpen] = useState(false);
    const [newKey, setNewKey] = useState("");
    const [newPriority, setNewPriority] = useState(1);
    const [saving, setSaving] = useState(false);

    const revalidateRelated = useCallback(() => {
        mutate();
        globalMutate("providers-with-keys"); // refresh agent create/edit dropdown
    }, [mutate, globalMutate]);

    const handleAdd = useCallback(async () => {
        if (!newKey.trim()) return;
        setSaving(true);
        try {
            await addProviderKey(provider.id, { api_key: newKey, priority: newPriority });
            toast.success(t("keyAdded"));
            revalidateRelated();
            setAddDialogOpen(false);
            setNewKey("");
            setNewPriority(1);
        } catch {
            toast.error(t("keyAddFailed"));
        } finally {
            setSaving(false);
        }
    }, [newKey, newPriority, provider.id, revalidateRelated, t]);

    const handleToggle = useCallback(async (keyId: string, active: boolean) => {
        try {
            await updateProviderKey(keyId, { is_active: active });
            revalidateRelated();
            toast.success(active ? t("keyEnabled") : t("keyDisabled"));
        } catch {
            toast.error(t("keyUpdateFailed"));
        }
    }, [revalidateRelated, t]);

    const handleDelete = useCallback(async (keyId: string) => {
        try {
            await deleteProviderKey(keyId);
            revalidateRelated();
            toast.success(t("keyDeleted"));
        } catch {
            toast.error(t("keyDeleteFailed"));
        }
    }, [revalidateRelated, t]);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="sm" onClick={onBack}>
                        ← {t("back")}
                    </Button>
                    <h2 className="text-lg font-semibold">{provider.name} — {t("apiKeys")}</h2>
                </div>
                {hasPermission("provider_key.create") && (
                    <Button size="sm" onClick={() => setAddDialogOpen(true)}>
                        <Plus className="h-4 w-4 mr-1" />
                        {t("addKey")}
                    </Button>
                )}
            </div>

            {!keys?.length ? (
                <Card>
                    <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
                        <Key className="h-12 w-12 text-muted-foreground/50" />
                        <p className="text-muted-foreground">{t("noKeys")}</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-3">
                    {keys.map((key: ProviderKey) => (
                        <Card key={key.id}>
                            <CardContent className="flex items-center justify-between p-4">
                                <div className="flex items-center gap-4">
                                    <Key className="h-4 w-4 text-muted-foreground" />
                                    <div>
                                        <p className="font-mono text-sm">{key.key_preview}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {t("priority")}: {key.priority}
                                            {key.cooldown_until && (
                                                <span className="ml-2 text-yellow-500">⏳ {t("cooldown")}</span>
                                            )}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <Switch
                                        checked={key.is_active}
                                        onCheckedChange={(checked) => handleToggle(key.id, checked)}
                                        disabled={!hasPermission("provider_key.update")}
                                    />
                                    {hasPermission("provider_key.delete") && (
                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <Button variant="ghost" size="icon" className="text-destructive">
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>{t("deleteKeyTitle")}</AlertDialogTitle>
                                                    <AlertDialogDescription>{t("deleteKeyDesc")}</AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
                                                    <AlertDialogAction onClick={() => handleDelete(key.id)}>
                                                        {tc("delete")}
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Add Key Dialog */}
            <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{t("addKeyTitle")}</DialogTitle>
                        <DialogDescription>{t("addKeyDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <Label>{t("apiKey")}</Label>
                            <Input
                                type="password"
                                value={newKey}
                                onChange={(e) => setNewKey(e.target.value)}
                                placeholder="sk-..."
                            />
                        </div>
                        <div>
                            <Label>{t("priority")}</Label>
                            <Input
                                type="number"
                                min={1}
                                value={newPriority}
                                onChange={(e) => setNewPriority(parseInt(e.target.value) || 1)}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
                            {tc("cancel")}
                        </Button>
                        <Button onClick={handleAdd} disabled={saving || !newKey.trim()}>
                            {saving ? t("saving") : t("addKey")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
