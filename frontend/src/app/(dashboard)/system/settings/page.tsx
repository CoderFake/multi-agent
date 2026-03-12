"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { SystemSetting } from "@/types/models";
import {
  fetchSystemSettings,
  updateSystemSetting,
} from "@/lib/api/system";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Pencil, Save, X } from "lucide-react";

export default function SystemSettingsPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);

  const { data, mutate, isLoading } = useSWR(
    "system-settings",
    fetchSystemSettings,
  );

  const startEdit = (setting: SystemSetting) => {
    setEditingKey(setting.key);
    setEditValue(setting.value);
  };

  const cancelEdit = () => {
    setEditingKey(null);
    setEditValue("");
  };

  const handleSave = useCallback(
    async (key: string) => {
      setSaving(true);
      try {
        await updateSystemSetting(key, { value: editValue });
        toast.success(t("updateSuccess"));
        cancelEdit();
        mutate();
      } catch {
        toast.error("Error");
      } finally {
        setSaving(false);
      }
    },
    [editValue, mutate, t],
  );

  return (
    <div>
      <PageHeader title={ts("settingsTitle")} description={ts("settingsDesc")} />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {(data ?? []).map((setting) => (
            <Card key={setting.key}>
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex-1 min-w-0">
                  <Label className="text-sm font-mono font-semibold">
                    {setting.key}
                  </Label>
                  {setting.description && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {setting.description}
                    </p>
                  )}
                </div>

                {editingKey === setting.key ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-64"
                    />
                    <Button
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleSave(setting.key)}
                      disabled={saving}
                    >
                      <Save className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={cancelEdit}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <code className="text-sm bg-muted px-2 py-1 rounded max-w-[300px] truncate">
                      {setting.value}
                    </code>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => startEdit(setting)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
