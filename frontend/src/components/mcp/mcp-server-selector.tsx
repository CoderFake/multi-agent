"use client";

import { useTranslations } from "next-intl";
import type { SystemMcpServer } from "@/types/models";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Save, Server, Building2, Globe, Shield } from "lucide-react";

interface McpServerSelectorProps {
  servers: SystemMcpServer[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSaveConfig?: () => void;
  onAssignOrgs?: () => void;
}

export function McpServerSelector({
  servers,
  selectedId,
  onSelect,
  onSaveConfig,
  onAssignOrgs,
}: McpServerSelectorProps) {
  const t = useTranslations("common");
  const ts = useTranslations("system");

  if (servers.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 p-4 text-center text-sm text-muted-foreground">
        {ts("selectServer")}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Server tabs/chips */}
      <div className="flex items-center gap-1.5 flex-wrap flex-1">
        <Server className="h-4 w-4 text-muted-foreground shrink-0" />
        {servers.map((server) => (
          <button
            key={server.id}
            onClick={() => onSelect(server.id)}
            className={`
              inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium
              transition-colors border cursor-pointer
              ${selectedId === server.id
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card text-foreground border-border/50 hover:bg-muted/50"
              }
            `}
          >
            {server.display_name || server.codename}
            <StatusBadge status={server.is_active} />
            {server.is_public ? (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                <Globe className="h-3 w-3 mr-0.5" />{ts("mcpPublic")}
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                <Shield className="h-3 w-3 mr-0.5" />{ts("mcpRestricted")}
              </Badge>
            )}
          </button>
        ))}
      </div>

      {/* Actions */}
      {selectedId && (onSaveConfig || onAssignOrgs) && (
        <div className="flex items-center gap-1.5">
          {onSaveConfig && (
            <Button variant="outline" size="sm" onClick={onSaveConfig} className="gap-1.5">
              <Save className="h-3.5 w-3.5" />
              {t("save")}
            </Button>
          )}
          {onAssignOrgs && (
            <Button
              variant="outline"
              size="sm"
              onClick={onAssignOrgs}
              className="gap-1.5"
              disabled={servers.find((s) => s.id === selectedId)?.is_public}
            >
              <Building2 className="h-3.5 w-3.5" />
              {ts("assignOrgs")}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
