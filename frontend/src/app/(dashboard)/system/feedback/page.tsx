"use client";

/**
 * Feedback admin page — superuser only.
 * Rule 1: datetime via formatDateTime. Rule 2: permission guard.
 * Rule 3: all text from i18n. Rule 4: API from lib/api/. Rule 5: SRP.
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { fetchFeedbackList, updateFeedbackStatus } from "@/lib/api/feedback";
import { formatDateTime } from "@/lib/datetime";
import type { Feedback } from "@/types/models";
import { toast } from "sonner";

const STATUSES = ["new", "reviewed", "resolved"] as const;

export default function FeedbackAdminPage() {
    const t = useTranslations("feedback");
    const tc = useTranslations("common");
    const [items, setItems] = useState<Feedback[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
    const [page, setPage] = useState(1);
    const pageSize = 20;

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchFeedbackList(statusFilter, page, pageSize);
            setItems(data.items);
            setTotal(data.total);
        } catch {
            toast.error("Failed to load feedback");
        } finally {
            setLoading(false);
        }
    }, [statusFilter, page]);

    useEffect(() => {
        load();
    }, [load]);

    const handleStatusUpdate = async (id: string, status: string) => {
        try {
            await updateFeedbackStatus(id, status);
            setItems((prev) =>
                prev.map((f) => (f.id === id ? { ...f, status } : f)),
            );
            toast.success(tc("updateSuccess"));
        } catch {
            toast.error("Failed to update status");
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case "new": return t("statusNew");
            case "reviewed": return t("statusReviewed");
            case "resolved": return t("statusResolved");
            default: return status;
        }
    };

    const getCategoryLabel = (category: string) => {
        switch (category) {
            case "bug": return t("bug");
            case "feature_request": return t("feature_request");
            case "question": return t("question");
            case "other": return t("other");
            default: return category;
        }
    };

    if (loading) return <LoadingSkeleton variant="table" />;

    return (
        <div className="space-y-6">
            <PageHeader title={t("adminTitle")} description={t("adminDesc")} />

            {/* Filters */}
            <div className="flex items-center gap-2">
                <Button
                    variant={!statusFilter ? "default" : "outline"}
                    size="sm"
                    onClick={() => { setStatusFilter(undefined); setPage(1); }}
                >
                    {t("allStatuses")}
                </Button>
                {STATUSES.map((s) => (
                    <Button
                        key={s}
                        variant={statusFilter === s ? "default" : "outline"}
                        size="sm"
                        onClick={() => { setStatusFilter(s); setPage(1); }}
                    >
                        {getStatusLabel(s)}
                    </Button>
                ))}
            </div>

            {/* Table */}
            {items.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground">{t("noFeedback")}</div>
            ) : (
                <div className="rounded-md border">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b bg-muted/50">
                                <th className="px-4 py-3 text-left text-sm font-medium">{t("from")}</th>
                                <th className="px-4 py-3 text-left text-sm font-medium">{t("category")}</th>
                                <th className="px-4 py-3 text-left text-sm font-medium">{t("message")}</th>
                                <th className="px-4 py-3 text-left text-sm font-medium">{tc("status")}</th>
                                <th className="px-4 py-3 text-left text-sm font-medium">{tc("createdAt")}</th>
                                <th className="px-4 py-3 text-left text-sm font-medium">{tc("actions")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map((fb) => (
                                <tr key={fb.id} className="border-b">
                                    <td className="px-4 py-3 text-sm">
                                        <div>{fb.user_full_name || "—"}</div>
                                        <div className="text-xs text-muted-foreground">{fb.user_email}</div>
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        <StatusBadge status={fb.category === "bug" ? "inactive" : "active"} label={getCategoryLabel(fb.category)} />
                                    </td>
                                    <td className="px-4 py-3 text-sm max-w-xs">
                                        <p className="line-clamp-2">{fb.message}</p>
                                        {fb.attachments && fb.attachments.length > 0 && (
                                            <span className="text-xs text-muted-foreground">
                                                📎 {fb.attachments.length} {t("attachments")}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        <StatusBadge
                                            status={
                                                fb.status === "resolved" ? "active" :
                                                    fb.status === "reviewed" ? "pending" : "inactive"
                                            }
                                            label={getStatusLabel(fb.status)}
                                        />
                                    </td>
                                    <td className="px-4 py-3 text-sm text-muted-foreground">
                                        {formatDateTime(fb.created_at)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="outline" size="sm">
                                                    {t("updateStatus")}
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent>
                                                {STATUSES.filter((s) => s !== fb.status).map((s) => (
                                                    <DropdownMenuItem
                                                        key={s}
                                                        onClick={() => handleStatusUpdate(fb.id, s)}
                                                    >
                                                        {getStatusLabel(s)}
                                                    </DropdownMenuItem>
                                                ))}
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Pagination info */}
            {total > 0 && (
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>
                        {tc("showing")} {items.length} {tc("of")} {total}
                    </span>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={page <= 1}
                            onClick={() => setPage((p) => p - 1)}
                        >
                            {tc("back")}
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={page * pageSize >= total}
                            onClick={() => setPage((p) => p + 1)}
                        >
                            {tc("next")}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
