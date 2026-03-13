"use client";

import dynamic from "next/dynamic";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { UserNav } from "@/components/layout/user-nav";

const ThemeToggle = dynamic(() => import("@/components/theme-toggle").then((m) => m.ThemeToggle), { ssr: false });
const NotificationBell = dynamic(() => import("@/components/layout/notification-bell").then((m) => m.NotificationBell), { ssr: false });
const LocaleSwitcher = dynamic(() => import("@/components/locale-switcher").then((m) => m.LocaleSwitcher), { ssr: false });

export function TopBar() {
  return (
    <header className="flex shrink-0 items-center gap-2 px-3 pt-4">
      <SidebarTrigger className="-ml-1" />

      {/* Breadcrumb placeholder — Sprint F5 */}
      <div className="flex-1" />

      {/* Right side actions */}
      <div className="flex items-center gap-1">
        <NotificationBell />
        <ThemeToggle />
        <LocaleSwitcher />
        <UserNav />
      </div>
    </header>
  );
}

