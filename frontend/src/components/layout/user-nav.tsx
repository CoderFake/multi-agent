"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { LogOut, Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { SettingsDialog } from "@/components/settings/settings-dialog";

export function UserNav() {
  const t = useTranslations("common");
  const { user, logout } = useAuth();
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-2">
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.full_name || "User"}
                className="h-7 w-7 rounded-full object-cover"
              />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                {user?.full_name?.charAt(0).toUpperCase() ?? "U"}
              </div>
            )}
            <span className="hidden md:inline-block text-sm truncate max-w-[120px]">
              {user?.full_name}
            </span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end">
          <DropdownMenuItem onClick={() => setSettingsOpen(true)} className="gap-2">
            <Settings className="h-4 w-4" />
            {t("settings")}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="gap-2 text-destructive" onClick={logout}>
            <LogOut className="h-4 w-4" />
            {t("logout")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
