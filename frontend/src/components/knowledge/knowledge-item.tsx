"use client";

import { useTranslations } from "next-intl";
import { usePermissions } from "@/hooks/use-permissions";
import {
    ContextMenu, ContextMenuContent, ContextMenuItem,
    ContextMenuSeparator, ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Badge } from "@/components/ui/badge";
import {
    Folder, FileText, Lock, Trash2, FolderOpen, Eye, Globe,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useIndexing } from "@/contexts/indexing-context";
import { IndexingProgressBar } from "@/components/shared/indexing-progress-bar";
import type { KnowledgeFolder, KnowledgeDocument } from "@/types/models";

function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ─── Folder Item ─── */

interface FolderItemProps {
    folder: KnowledgeFolder;
    onOpen: (folderId: string) => void;
    onDelete: (folderId: string) => void;
    onToggleAccess?: (folderId: string, currentAccess: string) => void;
}

export function FolderItem({ folder, onOpen, onDelete, onToggleAccess }: FolderItemProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const { hasPermission } = usePermissions();

    return (
        <ContextMenu>
            <ContextMenuTrigger asChild>
                <button
                    className={cn(
                        "flex flex-col items-center gap-2 p-4 rounded-xl",
                        "hover:bg-muted/60 transition-colors cursor-pointer",
                        "group w-full text-center",
                    )}
                    onClick={() => onOpen(folder.id)}
                >
                    <div className="relative">
                        <Folder className="h-12 w-12 text-blue-500" />
                        {folder.access_type === "restricted" && (
                            <Lock className="h-3.5 w-3.5 text-amber-500 absolute -bottom-0.5 -right-0.5 bg-background rounded-full p-0.5" />
                        )}
                    </div>
                    <div className="min-w-0 w-full">
                        <p className="text-sm font-medium truncate">{folder.name}</p>
                        <p className="text-xs text-muted-foreground">
                            {folder.document_count} {t("documents").toLowerCase()}
                        </p>
                    </div>
                </button>
            </ContextMenuTrigger>
            <ContextMenuContent>
                <ContextMenuItem onClick={() => onOpen(folder.id)}>
                    <FolderOpen className="h-4 w-4" />
                    {t("openFolder")}
                </ContextMenuItem>
                {hasPermission("folder.update") && onToggleAccess && (
                    <>
                        <ContextMenuSeparator />
                        <ContextMenuItem
                            onClick={() => onToggleAccess(folder.id, folder.access_type)}
                        >
                            {folder.access_type === "restricted" ? (
                                <Globe className="h-4 w-4" />
                            ) : (
                                <Lock className="h-4 w-4" />
                            )}
                            {folder.access_type === "restricted"
                                ? t("setPublic")
                                : t("setRestricted")}
                        </ContextMenuItem>
                    </>
                )}
                {hasPermission("folder.delete") && (
                    <>
                        <ContextMenuSeparator />
                        <ContextMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => onDelete(folder.id)}
                        >
                            <Trash2 className="h-4 w-4" />
                            {tc("delete")}
                        </ContextMenuItem>
                    </>
                )}
            </ContextMenuContent>
        </ContextMenu>
    );
}

/* ─── File (Document) Item ─── */

interface FileItemProps {
    document: KnowledgeDocument;
    onOpen: (docId: string) => void;
    onDelete: (docId: string) => void;
}

export function FileItem({ document: doc, onOpen, onDelete }: FileItemProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const { hasPermission } = usePermissions();
    const { progressMap } = useIndexing();

    const sseProgress = progressMap.get(doc.id);
    const isProcessing = sseProgress
        ? !["completed", "failed"].includes(sseProgress.status)
        : ["pending", "indexing"].includes(doc.index_status);

    // Derive effective status: SSE takes priority over stale DB value
    const effectiveStatus = sseProgress
        ? sseProgress.status === "completed" ? "indexed"
            : sseProgress.status === "failed" ? "failed"
                : doc.index_status
        : doc.index_status;

    return (
        <ContextMenu>
            <ContextMenuTrigger asChild>
                <div
                    className={cn(
                        "flex flex-col items-center gap-2 p-4 rounded-xl",
                        "hover:bg-muted/60 transition-colors cursor-pointer",
                        "group w-full text-center",
                    )}
                    onClick={() => onOpen(doc.id)}
                >
                    <div className="relative">
                        <FileText className="h-12 w-12 text-muted-foreground" />
                        {!isProcessing && (
                            <Badge
                                variant={
                                    effectiveStatus === "indexed" ? "default"
                                        : effectiveStatus === "failed" ? "destructive"
                                            : "secondary"
                                }
                                className="absolute -top-1 -right-2 text-[9px] h-4 px-1"
                            >
                                {effectiveStatus}
                            </Badge>
                        )}
                    </div>
                    <div className="min-w-0 w-full">
                        <p className="text-sm font-medium truncate">{doc.title}</p>
                        <p className="text-xs text-muted-foreground">
                            {doc.file_type.toUpperCase()} · {formatFileSize(doc.file_size)}
                        </p>
                    </div>
                    {isProcessing && (
                        <div className="w-full px-2">
                            <IndexingProgressBar
                                progress={sseProgress?.progress ?? 0}
                                status={sseProgress?.status ?? "queued"}
                                message={sseProgress?.message}
                                size="sm"
                            />
                        </div>
                    )}
                </div>
            </ContextMenuTrigger>
            <ContextMenuContent>
                <ContextMenuItem onClick={() => onOpen(doc.id)}>
                    <Eye className="h-4 w-4" />
                    {t("openFile")}
                </ContextMenuItem>
                {hasPermission("document.delete") && (
                    <>
                        <ContextMenuSeparator />
                        <ContextMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => onDelete(doc.id)}
                        >
                            <Trash2 className="h-4 w-4" />
                            {tc("delete")}
                        </ContextMenuItem>
                    </>
                )}
            </ContextMenuContent>
        </ContextMenu>
    );
}
