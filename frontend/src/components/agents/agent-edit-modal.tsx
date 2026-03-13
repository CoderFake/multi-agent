"use client";

import { useState, useCallback, useEffect } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import type { SystemAgent, AgentUpdateData } from "@/types/models";
import { updateSystemAgent, setAgentPublic } from "@/lib/api/system";
import { AgentOrgList } from "@/components/agents/agent-org-list";
import { AgentToolList } from "@/components/agents/agent-tool-list";
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
import { Button } from "@/components/ui/button";

interface AgentEditModalProps {
  agent: SystemAgent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function AgentEditModal({
  agent,
  open,
  onOpenChange,
  onSaved,
}: AgentEditModalProps) {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<AgentUpdateData>({});
  const [isPublic, setIsPublic] = useState(false);

  // Reset form when agent changes
  useEffect(() => {
    if (agent) {
      setFormData({
        display_name: agent.display_name,
        description: agent.description ?? "",
        is_active: agent.is_active,
      });
      setIsPublic(agent.is_public);
    }
  }, [agent]);

  const handleSave = useCallback(async () => {
    if (!agent) return;
    setSaving(true);
    try {
      // Update agent fields
      await updateSystemAgent(agent.id, formData);

      // Toggle is_public if changed
      if (isPublic !== agent.is_public) {
        await setAgentPublic(agent.id, isPublic);
      }

      toast.success(t("updateSuccess"));
      onSaved();
      onOpenChange(false);
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  }, [agent, formData, isPublic, onSaved, onOpenChange, t]);

  if (!agent) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {ts("editAgent")}:{" "}
            <code className="text-sm bg-muted px-1.5 py-0.5 rounded font-normal">
              {agent.codename}
            </code>
          </DialogTitle>
        </DialogHeader>

        {/* Agent fields */}
        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t("displayName")}</Label>
              <Input
                value={formData.display_name ?? ""}
                onChange={(e) =>
                  setFormData({ ...formData, display_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>{t("description")}</Label>
              <Textarea
                value={formData.description ?? ""}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows={1}
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <Switch
                checked={formData.is_active ?? true}
                onCheckedChange={(v) =>
                  setFormData({ ...formData, is_active: v })
                }
              />
              <Label>{t("active")}</Label>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={isPublic}
                onCheckedChange={setIsPublic}
              />
              <div>
                <Label>{ts("isPublic")}</Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {ts("publicDesc")}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Two-column: Org assignment (left) + Tools (right) */}
        <div className="grid grid-cols-2 gap-4 flex-1 min-h-0 overflow-hidden">
          <div className="space-y-2 overflow-hidden flex flex-col">
            <h3 className="font-semibold text-sm">
              {ts("assignedOrgs")}
            </h3>
            <div className="flex-1 overflow-y-auto">
              <AgentOrgList agentId={agent.id} isPublic={isPublic} />
            </div>
          </div>

          <div className="space-y-2 overflow-hidden flex flex-col">
            <h3 className="font-semibold text-sm">
              {ts("agentTools")}
            </h3>
            <div className="flex-1 overflow-y-auto">
              <AgentToolList agentId={agent.id} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("cancel")}
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? t("processing") : t("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
