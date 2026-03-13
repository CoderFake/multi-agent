"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import { OrgSwitcher } from "@/components/layout/org-switcher";
import { useTranslations } from "next-intl";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  Building2,
  Bot,
  Plug,
  Server,
  Settings,
  Users,
  Shield,
  FolderOpen,
  LayoutDashboard,
  ScrollText,
  MessageSquare,
  type LucideIcon,
} from "lucide-react";
import dynamic from "next/dynamic";

const FeedbackDialog = dynamic(() => import("@/components/layout/feedback-dialog").then((m) => m.FeedbackDialog), { ssr: false });

interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  permission?: string;
}

const systemNavItems: NavItem[] = [
  { title: "organizations", href: "/system/organizations", icon: Building2 },
  { title: "agents", href: "/system/agents", icon: Bot },
  { title: "providers", href: "/system/providers", icon: Plug },
  { title: "mcpServers", href: "/system/mcp-servers", icon: Server },
  { title: "feedback", href: "/system/feedback", icon: MessageSquare },
  { title: "settings", href: "/system/settings", icon: Settings },
];

const tenantNavItems: NavItem[] = [
  { title: "users", href: "/users", icon: Users, permission: "user.view" },
  { title: "groups", href: "/groups", icon: Shield, permission: "group.view" },
  { title: "agents", href: "/agents", icon: Bot, permission: "agent.view" },
  { title: "mcpServers", href: "/mcp-servers", icon: Server, permission: "mcp_server.view" },
  { title: "providers", href: "/providers", icon: Plug, permission: "provider.view" },
  { title: "knowledge", href: "/knowledge", icon: FolderOpen, permission: "folder.view" },
  { title: "permissions", href: "/permissions", icon: Shield, permission: "permission.view" },
  { title: "auditLogs", href: "/audit-logs", icon: ScrollText, permission: "audit_log.view" },
];

export function AppSidebar() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const { isSuperuser, orgId } = useCurrentOrg();
  const { canView } = usePermissions();

  const isActive = (href: string) => pathname.startsWith(href);

  // Build tenant prefix for dev routing
  const tenantPrefix = orgId ? `/t/${orgId}` : "";

  return (
    <Sidebar variant="floating" collapsible="icon" className="border-r-0">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard" className="flex items-center">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
                  C
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-blue-500 to-violet-500 bg-clip-text text-transparent">CMS Admin</span>
                  <span className="text-xs text-muted-foreground">v0.1.0</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Dashboard */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={isActive("/dashboard")}>
                  <Link href="/dashboard">
                    <LayoutDashboard className="h-4 w-4" />
                    <span>{t("dashboard")}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* System section — superuser only */}
        {isSuperuser && (
          <SidebarGroup>
            <SidebarGroupLabel>{t("system")}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {systemNavItems.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive(item.href)}
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{t(item.title)}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Tenant section — filtered by permissions */}
        {orgId && (
          <SidebarGroup>
            <SidebarGroupLabel>{t("organization")}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {tenantNavItems
                  .filter((item) => !item.permission || canView(item.permission.split(".")[0]))
                  .map((item) => {
                    const href = `${tenantPrefix}${item.href}`;
                    return (
                      <SidebarMenuItem key={item.href}>
                        <SidebarMenuButton asChild isActive={isActive(href)}>
                          <Link href={href}>
                            <item.icon className="h-4 w-4" />
                            <span>{t(item.title)}</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <FeedbackDialog />
          </SidebarMenuItem>
          <SidebarMenuItem>
            <OrgSwitcher />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
