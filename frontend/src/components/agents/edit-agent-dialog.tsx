"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { Agent, AgentUpdate, ProviderWithKeys, AgentModel } from "@/types/models";
import { updateTenantAgent, fetchProvidersWithKeys, fetchProviderModels, setAgentProvider } from "@/lib/api/agent-access";
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
import { AlertTriangle } from "lucide-react";

interface EditAgentDialogProps {
    agent: Agent;
    open: boolean;
    onOpenChange: (v: boolean) => void;
    onUpdated: () => void;
}

export function EditAgentDialog({ agent, open, onOpenChange, onUpdated }: EditAgentDialogProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<AgentUpdate>({
        display_name: agent.display_name,
        description: agent.description ?? "",
    });
    const [selectedProviderId, setSelectedProviderId] = useState<string>(agent.provider_id ?? "");
    const [selectedModelId, setSelectedModelId] = useState<string>(agent.model_id ?? "");

    // Sync when agent changes
    useEffect(() => {
        setForm({
            display_name: agent.display_name,
            description: agent.description ?? "",
        });
        setSelectedProviderId(agent.provider_id ?? "");
        setSelectedModelId(agent.model_id ?? "");
    }, [agent.id, agent.display_name, agent.description, agent.provider_id, agent.model_id]);

    // Fetch providers with keys
    const { data: providers } = useSWR<ProviderWithKeys[]>(
        open ? "providers-with-keys" : null,
        fetchProvidersWithKeys,
        { keepPreviousData: true },
    );

    // Fetch models for selected provider
    const { data: models } = useSWR<AgentModel[]>(
        selectedProviderId ? `provider-models-${selectedProviderId}` : null,
        () => fetchProviderModels(selectedProviderId),
    );

    // Reset model when provider changes (but NOT on initial load)
    const [providerChanged, setProviderChanged] = useState(false);
    useEffect(() => {
        if (providerChanged) {
            setSelectedModelId("");
            setProviderChanged(false);
        }
    }, [providerChanged]);

    const handleProviderChange = (value: string) => {
        setSelectedProviderId(value);
        setProviderChanged(true);
    };

    const handleSubmit = async () => {
        if (!form.display_name) return;
        setLoading(true);
        try {
            if (agent.is_system) {
                // For system agents, only set provider (can't update agent fields)
                if (selectedProviderId && selectedModelId) {
                    await setAgentProvider(agent.id, selectedProviderId, selectedModelId);
                }
            } else {
                // For custom agents, update agent fields + provider
                await updateTenantAgent(agent.id, {
                    ...form,
                    provider_id: selectedProviderId || undefined,
                    model_id: selectedModelId || undefined,
                });
            }
            toast.success(t("agentUpdated"));
            onOpenChange(false);
            onUpdated();
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
                    <DialogTitle>{agent.is_system ? t("configureProvider") : t("editAgent")}</DialogTitle>
                    <DialogDescription>{agent.codename}</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    {/* Name/description only for custom agents */}
                    {!agent.is_system && (
                        <>
                            <div className="space-y-1.5">
                                <Label className="text-xs">{t("displayName")}</Label>
                                <Input
                                    id="edit-agent-display-name"
                                    value={form.display_name ?? ""}
                                    onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label className="text-xs">{tc("description")}</Label>
                                <Textarea
                                    id="edit-agent-description"
                                    value={form.description ?? ""}
                                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    rows={3}
                                />
                            </div>
                        </>
                    )}

                    {/* Provider / Model selection — for ALL agents */}
                    <div className="space-y-1.5">
                        <Label className="text-xs">{t("selectProvider")}</Label>
                        {!providers || providers.length === 0 ? (
                            <div className="flex items-center gap-2 text-xs text-amber-500 bg-amber-500/10 rounded-md px-3 py-2">
                                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                {t("noProvidersWithKeys")}
                            </div>
                        ) : (
                            <Select value={selectedProviderId} onValueChange={handleProviderChange}>
                                <SelectTrigger id="edit-agent-provider">
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
                                <SelectTrigger id="edit-agent-model">
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
                        disabled={loading || (!agent.is_system && !form.display_name)}
                    >
                        {loading ? tc("loading") : tc("save")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
