"use client";

import React from "react";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { type ColumnDef } from "@tanstack/react-table";
import { PageHeader } from "@/components/shared/page-header";
import { PermissionGate } from "@/components/shared/permission-gate";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fetchTenantAuditLogs } from "@/lib/api/tenant";
import { useCurrentOrg } from "@/contexts/org-context";
import { formatDateTime } from "@/lib/datetime";
import type { AuditLog } from "@/types/models";

const ACTION_COLORS: Record<string, string> = {
    create: "bg-green-500/10 text-green-600",
    update: "bg-blue-500/10 text-blue-600",
    delete: "bg-red-500/10 text-red-600",
    upload: "bg-purple-500/10 text-purple-600",
    set_access: "bg-orange-500/10 text-orange-600",
    remove_access: "bg-orange-500/10 text-orange-600",
    enable: "bg-green-500/10 text-green-600",
    disable: "bg-yellow-500/10 text-yellow-600",
    default: "bg-muted text-muted-foreground",
};

const ACTION_TABS = ["all", "create", "update", "delete", "upload", "set_access", "remove_access"] as const;

export default function TenantAuditLogsPage() {
    const t = useTranslations("tenant");
    const { orgId } = useCurrentOrg();
    const [page, setPage] = useState(1);
    const [pageSize] = useState(20);
    const [actionFilter, setActionFilter] = useState("all");

    const { data, isLoading } = useSWR(
        orgId ? ["audit-logs", orgId, page, pageSize, actionFilter] : null,
        () => fetchTenantAuditLogs({
            page,
            pageSize,
            action: actionFilter !== "all" ? actionFilter : undefined,
        }),
    );

    // Reset page when filter changes
    const handleFilterChange = (value: string) => {
        setActionFilter(value);
        setPage(1);
    };

    const columns: ColumnDef<AuditLog, unknown>[] = useMemo(() => [
        {
            accessorKey: "action",
            header: t("action"),
            cell: ({ row }) => {
                const action = row.original.action;
                const color = ACTION_COLORS[action] || ACTION_COLORS.default;
                return (
                    <Badge className={`${color} border-0 font-mono text-xs`}>
                        {action}
                    </Badge>
                );
            },
        },
        {
            accessorKey: "resource_type",
            header: t("resourceType"),
            cell: ({ row }) => (
                <span className="font-medium">{row.original.resource_type}</span>
            ),
        },
        {
            accessorKey: "resource_id",
            header: "ID",
            cell: ({ row }) => (
                <span className="font-mono text-xs text-muted-foreground">
                    {row.original.resource_id
                        ? `${row.original.resource_id.slice(0, 8)}...`
                        : "—"
                    }
                </span>
            ),
        },
        {
            accessorKey: "user_email",
            header: t("user"),
            cell: ({ row }) => (
                <div>
                    <p className="text-sm">{row.original.user_email || "—"}</p>
                    {row.original.user_full_name && (
                        <p className="text-xs text-muted-foreground">{row.original.user_full_name}</p>
                    )}
                </div>
            ),
        },
        {
            accessorKey: "created_at",
            header: t("time"),
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatDateTime(row.original.created_at)}
                </span>
            ),
        },
    ], [t]);

    return (
        <PermissionGate permission="audit_log.view" pageLevel>
            <div className="flex flex-col h-[calc(100vh-64px)] gap-4">
                <PageHeader title={t("auditLogsTitle")} description={t("auditLogsDesc")} />

                <Card className="flex-1 min-h-0 flex flex-col overflow-hidden">
                    {/* Tab filter */}
                    <div className="border-b border-border/50 px-4 pt-3 shrink-0">
                        <Tabs value={actionFilter} onValueChange={handleFilterChange}>
                            <TabsList className="bg-transparent h-auto p-0 gap-0">
                                {ACTION_TABS.map((tab) => (
                                    <TabsTrigger
                                        key={tab}
                                        value={tab}
                                        className="rounded-none border-b-2 border-transparent px-4 pb-3 pt-1.5 text-sm data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
                                    >
                                        {tab === "all" ? t("allActions") : tab}
                                    </TabsTrigger>
                                ))}
                            </TabsList>
                        </Tabs>
                    </div>

                    {/* Table — only this part scrolls */}
                    <div className="flex-1 min-h-0 overflow-auto">
                        <table className="w-full text-sm">
                            <thead className="sticky top-0 bg-muted/80 backdrop-blur-sm z-10">
                                <tr className="border-b border-border/50">
                                    {columns.map((col, i) => (
                                        <th key={i} className="px-4 py-3 text-left font-medium text-muted-foreground">
                                            {typeof col.header === "string" ? col.header : ""}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {isLoading ? (
                                    Array.from({ length: 5 }).map((_, i) => (
                                        <tr key={i} className="border-b border-border/40">
                                            {columns.map((_, j) => (
                                                <td key={j} className="px-4 py-3">
                                                    <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                                                </td>
                                            ))}
                                        </tr>
                                    ))
                                ) : !data?.items?.length ? (
                                    <tr>
                                        <td colSpan={columns.length} className="text-center py-12 text-muted-foreground">
                                            {t("noAuditLogs")}
                                        </td>
                                    </tr>
                                ) : (
                                    data.items.map((log: AuditLog) => (
                                        <tr key={log.id} className="border-b border-border/40 last:border-b-0 hover:bg-muted/30 transition-colors">
                                            {columns.map((col, i) => (
                                                <td key={i} className="px-4 py-3">
                                                    {col.cell
                                                        ? (col.cell as (info: { row: { original: AuditLog } }) => React.ReactNode)({ row: { original: log } })
                                                        : String((log as unknown as Record<string, unknown>)[(col as { accessorKey?: string }).accessorKey ?? ""] ?? "")
                                                    }
                                                </td>
                                            ))}
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination — fixed at bottom */}
                    {!isLoading && (data?.total ?? 0) > 0 && (
                        <div className="shrink-0 border-t border-border/50 px-4 py-3">
                            <DataTablePagination
                                page={page}
                                pageSize={pageSize}
                                total={data?.total ?? 0}
                                pageCount={Math.ceil((data?.total ?? 0) / pageSize)}
                                onPageChange={setPage}
                            />
                        </div>
                    )}
                </Card>
            </div>
        </PermissionGate>
    );
}
