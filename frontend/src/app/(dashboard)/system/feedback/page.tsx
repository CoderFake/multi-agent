"use client";

/**
 * Feedback admin page — superuser only.
 * Uses DataTable-style table. Click row → detail modal with images.
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
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { fetchFeedbackList, updateFeedbackStatus } from "@/lib/api/feedback";
import { formatDateTime } from "@/lib/datetime";
import type { Feedback } from "@/types/models";
import { toast } from "sonner";
import { Paperclip, X, ChevronLeft, ChevronRight } from "lucide-react";

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

    // Detail modal
    const [selected, setSelected] = useState<Feedback | null>(null);
    const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

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
            // Also update selected item if open
            setSelected((prev) => prev?.id === id ? { ...prev, status } : prev);
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

            {/* Table — DataTable style */}
            {items.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground">{t("noFeedback")}</div>
            ) : (
                <div className="rounded-lg border border-border/50 bg-card">
                    <div className="relative overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border/50 bg-muted/30">
                                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("from")}</th>
                                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("category")}</th>
                                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("message")}</th>
                                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{tc("status")}</th>
                                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{tc("createdAt")}</th>
                                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{tc("actions")}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items.map((fb) => (
                                    <tr
                                        key={fb.id}
                                        className="border-b border-border/40 last:border-b-0 transition-colors hover:bg-muted/30 cursor-pointer"
                                        onClick={() => setSelected(fb)}
                                    >
                                        <td className="px-4 py-3">
                                            <div className="font-medium">{fb.user_full_name || "—"}</div>
                                            <div className="text-xs text-muted-foreground">{fb.user_email}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <StatusBadge status={fb.category === "bug" ? "inactive" : "active"} label={getCategoryLabel(fb.category)} />
                                        </td>
                                        <td className="px-4 py-3 max-w-xs">
                                            <p className="line-clamp-2">{fb.message}</p>
                                            {fb.attachments && fb.attachments.length > 0 && (
                                                <span className="inline-flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                                                    <Paperclip className="h-3 w-3" />
                                                    {fb.attachments.length} {t("attachments")}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <StatusBadge
                                                status={
                                                    fb.status === "resolved" ? "active" :
                                                        fb.status === "reviewed" ? "pending" : "inactive"
                                                }
                                                label={getStatusLabel(fb.status)}
                                            />
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                                            {formatDateTime(fb.created_at)}
                                        </td>
                                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
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
                </div>
            )}

            {/* Pagination */}
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

            {/* ═══ Detail Modal ═══ */}
            <Dialog open={!!selected} onOpenChange={(open) => { if (!open) setSelected(null); }}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{t("detailTitle")}</DialogTitle>
                    </DialogHeader>

                    {selected && (
                        <div className="space-y-4">
                            {/* Meta info */}
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div>
                                    <p className="text-xs text-muted-foreground mb-0.5">{t("from")}</p>
                                    <p className="font-medium">{selected.user_full_name || "—"}</p>
                                    <p className="text-xs text-muted-foreground">{selected.user_email}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-0.5">{t("category")}</p>
                                    <StatusBadge
                                        status={selected.category === "bug" ? "inactive" : "active"}
                                        label={getCategoryLabel(selected.category)}
                                    />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-0.5">{tc("status")}</p>
                                    <StatusBadge
                                        status={
                                            selected.status === "resolved" ? "active" :
                                                selected.status === "reviewed" ? "pending" : "inactive"
                                        }
                                        label={getStatusLabel(selected.status)}
                                    />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-0.5">{tc("createdAt")}</p>
                                    <p className="text-sm">{formatDateTime(selected.created_at)}</p>
                                </div>
                            </div>

                            {/* Message */}
                            <div>
                                <p className="text-xs text-muted-foreground mb-1.5">{t("message")}</p>
                                <div className="rounded-lg bg-muted/50 p-3 text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
                                    {selected.message}
                                </div>
                            </div>

                            {/* Attachments / Images */}
                            {selected.attachments && selected.attachments.length > 0 && (
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1.5">
                                        {t("attachments")} ({selected.attachments.length})
                                    </p>
                                    <div className="grid grid-cols-3 gap-2">
                                        {selected.attachments.map((url, i) => (
                                            <button
                                                key={i}
                                                type="button"
                                                onClick={() => setLightboxIndex(i)}
                                                className="relative aspect-square rounded-lg overflow-hidden border border-border/50 hover:ring-2 hover:ring-primary/50 transition-all cursor-pointer"
                                            >
                                                <img
                                                    src={url}
                                                    alt={`${t("attachments")} ${i + 1}`}
                                                    className="h-full w-full object-cover"
                                                />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Status update from modal */}
                            <div className="flex items-center justify-between pt-2 border-t border-border/50">
                                <p className="text-xs text-muted-foreground">{t("updateStatus")}</p>
                                <div className="flex gap-2">
                                    {STATUSES.filter((s) => s !== selected.status).map((s) => (
                                        <Button
                                            key={s}
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleStatusUpdate(selected.id, s)}
                                        >
                                            {getStatusLabel(s)}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* ═══ Image Lightbox ═══ */}
            <Dialog open={lightboxIndex !== null} onOpenChange={(open) => { if (!open) setLightboxIndex(null); }}>
                <DialogContent className="max-w-3xl p-0 bg-black/95 border-none">
                    <DialogTitle className="sr-only">{t("attachments")}</DialogTitle>
                    {lightboxIndex !== null && selected?.attachments && (
                        <div className="relative flex items-center justify-center min-h-[400px]">
                            {/* Close */}
                            <button
                                onClick={() => setLightboxIndex(null)}
                                className="absolute top-3 right-3 z-10 rounded-full bg-white/10 p-2 text-white hover:bg-white/20 transition-colors"
                            >
                                <X className="h-5 w-5" />
                            </button>

                            {/* Previous */}
                            {selected.attachments.length > 1 && (
                                <button
                                    onClick={() => setLightboxIndex(
                                        (lightboxIndex - 1 + selected.attachments!.length) % selected.attachments!.length
                                    )}
                                    className="absolute left-3 z-10 rounded-full bg-white/10 p-2 text-white hover:bg-white/20 transition-colors"
                                >
                                    <ChevronLeft className="h-5 w-5" />
                                </button>
                            )}

                            {/* Image */}
                            <img
                                src={selected.attachments[lightboxIndex]}
                                alt={`${t("attachments")} ${lightboxIndex + 1}`}
                                className="max-h-[80vh] max-w-full object-contain p-4"
                            />

                            {/* Next */}
                            {selected.attachments.length > 1 && (
                                <button
                                    onClick={() => setLightboxIndex(
                                        (lightboxIndex + 1) % selected.attachments!.length
                                    )}
                                    className="absolute right-3 z-10 rounded-full bg-white/10 p-2 text-white hover:bg-white/20 transition-colors"
                                >
                                    <ChevronRight className="h-5 w-5" />
                                </button>
                            )}

                            {/* Counter */}
                            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 text-white/70 text-sm">
                                {lightboxIndex + 1} / {selected.attachments.length}
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
