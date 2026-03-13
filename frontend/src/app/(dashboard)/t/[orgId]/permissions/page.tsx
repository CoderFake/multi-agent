"use client";

import { useState, useCallback, useMemo } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { Permission, TenantUser } from "@/types/models";
import { fetchTenantPermissions, fetchTenantUsers } from "@/lib/api/tenant";
import { api } from "@/lib/api-client";
import { useCurrentOrg } from "@/contexts/org-context";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Combobox } from "@/components/ui/combobox";
import {
    Search, CheckCircle, XCircle,
    Users, Building2, Bot, Plug, FolderOpen, Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

// ── Resource group definitions ──────────────────────────────────────
interface ResourceGroup {
    label: string;
    resources: string[];
    icon: LucideIcon;
}

const RESOURCE_GROUPS: ResourceGroup[] = [
    { label: "Auth & RBAC", resources: ["user", "group", "permission", "invite"], icon: Users },
    { label: "Organization", resources: ["organization"], icon: Building2 },
    { label: "Agent & MCP", resources: ["agent", "mcp_server", "agent_mcp", "tool", "tool_access", "ui_component"], icon: Bot },
    { label: "Provider", resources: ["provider", "provider_key"], icon: Plug },
    { label: "Knowledge", resources: ["folder", "document"], icon: FolderOpen },
    { label: "System", resources: ["system_setting", "audit_log", "feedback", "notification"], icon: Settings },
];

const RESOURCE_LABELS: Record<string, string> = {
    user: "User", organization: "Organization", group: "Group",
    permission: "Permission", invite: "Invite", agent: "Agent",
    mcp_server: "MCP Server", agent_mcp: "Agent MCP",
    tool: "Tool", tool_access: "Tool Access",
    ui_component: "UI Component",
    provider: "Provider", provider_key: "Provider Key",
    folder: "Folder", document: "Document",
    system_setting: "System Setting", audit_log: "Audit Log",
    feedback: "Feedback", notification: "Notification",
};

const ACTION_COLORS: Record<string, string> = {
    view: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    create: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    update: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    delete: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    invite: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
    assign: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
    revoke: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    deploy: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
    upload: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
    export: "bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400",
    resend: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
    attach: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    detach: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
};

export default function TenantPermissionsPage() {
    const t = useTranslations("common");
    const tp = useTranslations("tenant");
    const { orgId } = useCurrentOrg();

    // Permission check tool
    const [checkUserId, setCheckUserId] = useState("");
    const [checkCodename, setCheckCodename] = useState("");
    const [checkResult, setCheckResult] = useState<{
        granted: boolean;
        reason: string;
    } | null>(null);
    const [checking, setChecking] = useState(false);

    const { data: permissions, isLoading } = useSWR(
        orgId ? ["tenant-permissions", orgId] : null,
        () => fetchTenantPermissions(),
    );

    // Fetch tenant users for the check tool dropdown
    const { data: usersData } = useSWR(
        orgId ? ["tenant-users-check", orgId] : null,
        () => fetchTenantUsers({ page: 1, pageSize: 100 }),
    );

    // Group permissions by resource
    const permByResource = useMemo(() => {
        const map: Record<string, Permission[]> = {};
        (permissions ?? []).forEach((p: Permission) => {
            const resource = p.codename.split(".")[0] || "other";
            if (!map[resource]) map[resource] = [];
            map[resource].push(p);
        });
        return map;
    }, [permissions]);

    const handleCheck = useCallback(async () => {
        if (!checkUserId || !checkCodename) return;
        setChecking(true);
        try {
            const result = await api.post<{ granted: boolean; reason: string }>(
                "/permissions/check",
                { user_id: checkUserId, codename: checkCodename },
            );
            setCheckResult(result);
        } catch {
            toast.error(t("error"));
        } finally {
            setChecking(false);
        }
    }, [checkUserId, checkCodename, t]);

    const users = usersData?.items ?? [];

    return (
        <div className="flex flex-col h-[calc(100vh-100px)]">
            <div className="shrink-0">
                <PageHeader
                    title={tp("permissionsTitle")}
                    description={`${tp("permissionsDesc")} — ${(permissions ?? []).length} ${tp("permissions").toLowerCase()}`}
                />

                {/* Permission Check Tool */}
                <Card className="mb-4">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Search className="h-5 w-5" />
                            {tp("permissionCheck")}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col sm:flex-row gap-3 items-end">
                            <div className="flex-1 space-y-1">
                                <Label className="text-xs">{tp("selectUser")}</Label>
                                <Combobox
                                    options={users.map((u: TenantUser) => ({
                                        value: u.user_id,
                                        label: u.full_name,
                                        description: u.email,
                                    }))}
                                    value={checkUserId}
                                    onValueChange={setCheckUserId}
                                    placeholder={tp("selectUser")}
                                    searchPlaceholder={t("search")}
                                    emptyText={t("noData")}
                                />
                            </div>
                            <div className="flex-1 space-y-1">
                                <Label className="text-xs">{tp("permissions")}</Label>
                                <Combobox
                                    options={(permissions ?? []).map((p: Permission) => ({
                                        value: p.codename,
                                        label: p.codename,
                                        description: p.name,
                                    }))}
                                    value={checkCodename}
                                    onValueChange={setCheckCodename}
                                    placeholder={tp("selectPermission")}
                                    searchPlaceholder={t("search")}
                                    emptyText={t("noData")}
                                />
                            </div>
                            <Button
                                onClick={handleCheck}
                                disabled={checking || !checkUserId || !checkCodename}
                                size="sm"
                            >
                                {checking ? t("processing") : tp("check")}
                            </Button>
                        </div>
                        {checkResult && (
                            <div
                                className={`mt-3 p-3 rounded-lg border flex items-center gap-2 ${checkResult.granted
                                    ? "bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800"
                                    : "bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-800"
                                    }`}
                            >
                                {checkResult.granted ? (
                                    <CheckCircle className="h-5 w-5 text-green-600" />
                                ) : (
                                    <XCircle className="h-5 w-5 text-red-600" />
                                )}
                                <div>
                                    <span className="font-medium text-sm">
                                        {checkResult.granted ? tp("granted") : tp("denied")}
                                    </span>
                                    <p className="text-xs text-muted-foreground">
                                        {tp("reason")}: {checkResult.reason}
                                    </p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Permission List — scrollable within content */}
            <div className="flex-1 overflow-y-auto min-h-0">
                {isLoading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-32 rounded-lg bg-muted animate-pulse" />
                        ))}
                    </div>
                ) : (
                    <div className="space-y-4 pb-4">
                        {RESOURCE_GROUPS.map((group) => {
                            const groupPerms = group.resources.flatMap(
                                (r) => permByResource[r] ?? [],
                            );
                            if (groupPerms.length === 0) return null;
                            const GroupIcon = group.icon;

                            return (
                                <Card key={group.label}>
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <GroupIcon className="h-5 w-5 text-primary" />
                                            {group.label}
                                            <Badge variant="secondary" className="ml-2 text-xs">
                                                {groupPerms.length}
                                            </Badge>
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {group.resources.map((resource) => {
                                                const perms = permByResource[resource];
                                                if (!perms || perms.length === 0) return null;

                                                return (
                                                    <div key={resource} className="flex items-start gap-3">
                                                        <span className="text-sm font-medium text-muted-foreground w-32 shrink-0 pt-0.5">
                                                            {RESOURCE_LABELS[resource] ?? resource}
                                                        </span>
                                                        <div className="flex flex-wrap gap-1.5">
                                                            {perms.map((perm) => {
                                                                const action = perm.codename.split(".")[1] ?? "";
                                                                const color = ACTION_COLORS[action] ?? "bg-muted text-muted-foreground";
                                                                return (
                                                                    <span
                                                                        key={perm.id}
                                                                        className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${color}`}
                                                                        title={perm.name}
                                                                    >
                                                                        {action}
                                                                    </span>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
