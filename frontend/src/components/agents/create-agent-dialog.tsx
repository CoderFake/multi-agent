"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import type { AgentCreate } from "@/types/models";
import { createTenantAgent } from "@/lib/api/agent-access";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Plus } from "lucide-react";

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

    const handleSubmit = async () => {
        if (!form.codename || !form.display_name) return;
        setLoading(true);
        try {
            await createTenantAgent(form);
            toast.success(t("agentCreated"));
            setForm({ codename: "", display_name: "", description: "" });
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
            <DialogContent className="max-w-md">
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
