"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { AgentCreate, ProviderWithKeys, AgentModel } from "@/types/models";
import { createTenantAgent, fetchProvidersWithKeys, fetchProviderModels } from "@/lib/api/agent-access";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Plus, AlertTriangle } from "lucide-react";

interface CreateAgentDialogProps {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    onCreated: () => void;
}

export function CreateAgentDialog({ open, onOpenChange, onCreated }: CreateAgentDialogProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<AgentCreate>({
        codename: "",
        display_name: "",
        description: "",
    });
    const [selectedProviderId, setSelectedProviderId] = useState<string>("");
    const [selectedModelId, setSelectedModelId] = useState<string>("");

    // Fetch providers with keys
    const { data: providers } = useSWR<ProviderWithKeys[]>(
        open ? "providers-with-keys" : null,
        fetchProvidersWithKeys,
    );

    // Fetch models for selected provider
    const { data: models } = useSWR<AgentModel[]>(
        selectedProviderId ? `provider-models-${selectedProviderId}` : null,
        () => fetchProviderModels(selectedProviderId),
    );

    // Reset model when provider changes
    useEffect(() => {
        setSelectedModelId("");
    }, [selectedProviderId]);

    const handleSubmit = async () => {
        if (!form.codename || !form.display_name) return;
        setLoading(true);
        try {
            await createTenantAgent({
                ...form,
                provider_id: selectedProviderId || undefined,
                model_id: selectedModelId || undefined,
            });
            toast.success(t("agentCreated"));
            setForm({ codename: "", display_name: "", description: "" });
            setSelectedProviderId("");
            setSelectedModelId("");
            onOpenChange(false);
            onCreated();
        } catch {
            toast.error(t("error"));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{t("createAgent")}</DialogTitle>
                    <DialogDescription>{t("createAgentDesc")}</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="space-y-1.5">
                        <Label className="text-xs">Codename</Label>
                        <Input
                            id="agent-codename"
                            value={form.codename}
                            onChange={(e) => setForm({ ...form, codename: e.target.value })}
                            placeholder="my_custom_agent"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label className="text-xs">{t("displayName")}</Label>
                        <Input
                            id="agent-display-name"
                            value={form.display_name}
                            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                            placeholder="My Custom Agent"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label className="text-xs">{tc("description")}</Label>
                        <Textarea
                            id="agent-description"
                            value={form.description ?? ""}
                            onChange={(e) => setForm({ ...form, description: e.target.value })}
                            rows={3}
                        />
                    </div>

                    {/* Provider / Model selection */}
                    <div className="space-y-1.5">
                        <Label className="text-xs">{t("selectProvider")}</Label>
                        {!providers || providers.length === 0 ? (
                            <div className="flex items-center gap-2 text-xs text-amber-500 bg-amber-500/10 rounded-md px-3 py-2">
                                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                {t("noProvidersWithKeys")}
                            </div>
                        ) : (
                            <Select value={selectedProviderId} onValueChange={setSelectedProviderId}>
                                <SelectTrigger id="agent-provider">
                                    <SelectValue placeholder={t("selectProvider")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {providers.map((p) => (
                                        <SelectItem key={p.id} value={p.id}>
                                            {p.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                    </div>

                    {selectedProviderId && (
                        <div className="space-y-1.5">
                            <Label className="text-xs">{t("selectModel")}</Label>
                            <Select value={selectedModelId} onValueChange={setSelectedModelId}>
                                <SelectTrigger id="agent-model">
                                    <SelectValue placeholder={t("selectModel")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {(models ?? [])
                                        .filter((m) => m.model_type === "chat")
                                        .map((m) => (
                                            <SelectItem key={m.id} value={m.id}>
                                                {m.name}
                                            </SelectItem>
                                        ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>{tc("cancel")}</Button>
                    <Button
                        onClick={handleSubmit}
                        disabled={loading || !form.codename || !form.display_name}
                    >
                        {loading ? tc("loading") : tc("create")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

/** Trigger button for create agent — use separately with PermissionGate. */
export function CreateAgentButton({ onClick }: { onClick: () => void }) {
    const t = useTranslations("tenant");

    return (
        <Button size="sm" onClick={onClick} className="gap-1.5">
            <Plus className="h-4 w-4" /> {t("createAgent")}
        </Button>
    );
}
