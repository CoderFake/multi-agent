"use client";

import { useState } from "react";
import { useCurrentOrg } from "@/contexts/org-context";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Building2, ChevronsUpDown, Check, Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { OrgSettingsDialog } from "@/components/settings/org-settings-dialog";

export function OrgSwitcher() {
  const t = useTranslations("common");
  const { currentOrg, memberships, switchOrg } = useCurrentOrg();
  const [settingsOpen, setSettingsOpen] = useState(false);

  if (memberships.length === 0) return null;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between gap-2 px-2 h-10"
          >
            <div className="flex items-center gap-2 truncate">
              <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-sm font-medium">
                {currentOrg?.org_name ?? t("selectOrg")}
              </span>
            </div>
            <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="start" side="right">
          <DropdownMenuLabel>{t("organizations")}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {memberships.map((m) => (
            <DropdownMenuItem
              key={m.org_id}
              onClick={() => switchOrg(m.org_id)}
              className="gap-2"
            >
              <Building2 className="h-4 w-4" />
              <span className="truncate flex-1">{m.org_name}</span>
              {m.org_id === currentOrg?.org_id && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </DropdownMenuItem>
          ))}
          {currentOrg && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => setSettingsOpen(true)}
                className="gap-2"
              >
                <Settings className="h-4 w-4" />
                {t("settings")}
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <OrgSettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
