"use client";

import { useState, useCallback, useMemo, useRef } from "react";
import { useTranslations } from "next-intl";
import { usePermissions } from "@/hooks/use-permissions";
import useSWR from "swr";
import { toast } from "sonner";
import {
    ContextMenu, ContextMenuContent, ContextMenuItem,
    ContextMenuSeparator, ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
    DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FolderPlus, FileUp, Globe, Lock, FolderOpen } from "lucide-react";
import {
    createFolder, deleteFolder, updateFolder,
    fetchDocuments, uploadDocument, deleteDocument,
} from "@/lib/api/knowledge";
import { useIndexing } from "@/contexts/indexing-context";
import { FolderItem, FileItem } from "./knowledge-item";
import { DocumentPreview } from "./document-preview";
import type { KnowledgeFolder, KnowledgeDocument } from "@/types/models";

interface KnowledgeGridProps {
    folders: KnowledgeFolder[];
    currentFolderId: string | null;
    onOpenFolder: (folderId: string) => void;
    onMutateFolders: () => void;
}

export function KnowledgeGrid({
    folders,
    currentFolderId,
    onOpenFolder,
    onMutateFolders,
}: KnowledgeGridProps) {
    const t = useTranslations("tenant");
    const tc = useTranslations("common");
    const { hasPermission } = usePermissions();
    const { refresh: refreshIndexing } = useIndexing();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Child folders of current
    const childFolders = useMemo(
        () => folders.filter((f) =>
            currentFolderId ? f.parent_id === currentFolderId : !f.parent_id
        ),
        [folders, currentFolderId],
    );

    // Documents in current folder
    const { data: docs, mutate: mutateDocs } = useSWR(
        currentFolderId ? `docs-${currentFolderId}` : null,
        () => fetchDocuments(currentFolderId!),
    );

    // Create folder dialog state
    const [createFolderOpen, setCreateFolderOpen] = useState(false);
    const [newName, setNewName] = useState("");
    const [newDesc, setNewDesc] = useState("");
    const [newAccessType, setNewAccessType] = useState("public");
    const [saving, setSaving] = useState(false);

    // Delete confirm state
    const [deleteTarget, setDeleteTarget] = useState<
        { type: "folder" | "document"; id: string; name: string } | null
    >(null);

    // Upload state
    const [uploading, setUploading] = useState(false);

    // Preview state
    const [previewDocId, setPreviewDocId] = useState<string | null>(null);
    const previewDocName = useMemo(() => {
        if (!previewDocId || !docs) return "";
        const doc = docs.find((d: KnowledgeDocument) => d.id === previewDocId);
        return doc?.title ?? doc?.file_name ?? "";
    }, [previewDocId, docs]);

    // Toggle access state
    const [toggleAccessTarget, setToggleAccessTarget] = useState<
        { folderId: string; currentAccess: string } | null
    >(null);

    const handleCreateFolder = useCallback(async () => {
        if (!newName.trim()) return;
        setSaving(true);
        try {
            await createFolder({
                name: newName,
                description: newDesc || undefined,
                access_type: newAccessType,
                parent_id: currentFolderId ?? undefined,
            });
            toast.success(t("folderCreated"));
            onMutateFolders();
            setCreateFolderOpen(false);
            setNewName("");
            setNewDesc("");
            setNewAccessType("public");
        } catch {
            toast.error(t("folderCreateFailed"));
        } finally {
            setSaving(false);
        }
    }, [newName, newDesc, newAccessType, currentFolderId, onMutateFolders, t]);

    const handleUpload = useCallback(async (file: File) => {
        if (!currentFolderId) return;
        setUploading(true);
        try {
            await uploadDocument(file.name.replace(/\.[^.]+$/, ""), currentFolderId, file);
            toast.success(t("docUploaded"));
            mutateDocs();
            refreshIndexing();
        } catch {
            toast.error(t("docUploadFailed"));
        } finally {
            setUploading(false);
        }
    }, [currentFolderId, mutateDocs, refreshIndexing, t]);

    const handleDeleteConfirm = useCallback(async () => {
        if (!deleteTarget) return;
        try {
            if (deleteTarget.type === "folder") {
                await deleteFolder(deleteTarget.id);
                toast.success(t("folderDeleted"));
                onMutateFolders();
            } else {
                await deleteDocument(deleteTarget.id);
                toast.success(t("docDeleted"));
                mutateDocs();
            }
        } catch {
            toast.error(
                deleteTarget.type === "folder" ? t("folderDeleteFailed") : t("docDeleteFailed"),
            );
        } finally {
            setDeleteTarget(null);
        }
    }, [deleteTarget, onMutateFolders, mutateDocs, t]);

    const handleDeleteFolder = useCallback((folderId: string) => {
        const folder = folders.find((f) => f.id === folderId);
        setDeleteTarget({ type: "folder", id: folderId, name: folder?.name ?? "" });
    }, [folders]);

    const handleDeleteDoc = useCallback((docId: string) => {
        const doc = docs?.find((d: KnowledgeDocument) => d.id === docId);
        setDeleteTarget({ type: "document", id: docId, name: doc?.title ?? "" });
    }, [docs]);

    const handleToggleAccess = useCallback(async () => {
        if (!toggleAccessTarget) return;
        const newAccess = toggleAccessTarget.currentAccess === "public" ? "restricted" : "public";
        try {
            await updateFolder(toggleAccessTarget.folderId, { access_type: newAccess });
            toast.success(newAccess === "public" ? t("folderSetPublic") : t("folderSetRestricted"));
            onMutateFolders();
        } catch {
            toast.error(t("folderUpdateFailed"));
        } finally {
            setToggleAccessTarget(null);
        }
    }, [toggleAccessTarget, onMutateFolders, t]);

    const isEmpty = childFolders.length === 0 && (!docs || docs.length === 0);

    return (
        <>
            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.png,.jpg,.jpeg"
                onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                    e.target.value = "";
                }}
            />

            {/* Grid with right-click on empty space */}
            <ContextMenu>
                <ContextMenuTrigger asChild>
                    <div className="min-h-[400px] rounded-xl border bg-card p-4">
                        {isEmpty ? (
                            <div className="flex flex-col items-center justify-center h-[400px] gap-3 text-muted-foreground">
                                <FolderOpen className="h-16 w-16 opacity-30" />
                                <p className="text-sm">{currentFolderId ? t("emptyFolder") : t("noFolders")}</p>
                                <p className="text-xs opacity-60">{t("rightClickHint")}</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-1">
                                {childFolders.map((folder) => (
                                    <FolderItem
                                        key={folder.id}
                                        folder={folder}
                                        onOpen={onOpenFolder}
                                        onDelete={handleDeleteFolder}
                                        onToggleAccess={(fid, access) => setToggleAccessTarget({ folderId: fid, currentAccess: access })}
                                    />
                                ))}
                                {docs?.map((doc: KnowledgeDocument) => (
                                    <FileItem
                                        key={doc.id}
                                        document={doc}
                                        onOpen={(docId) => setPreviewDocId(docId)}
                                        onDelete={handleDeleteDoc}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </ContextMenuTrigger>
                <ContextMenuContent>
                    {hasPermission("folder.create") && (
                        <ContextMenuItem onClick={() => {
                            setNewName("");
                            setNewDesc("");
                            setNewAccessType("public");
                            setCreateFolderOpen(true);
                        }}>
                            <FolderPlus className="h-4 w-4" />
                            {t("newFolder")}
                        </ContextMenuItem>
                    )}
                    {currentFolderId && hasPermission("document.upload") && (
                        <ContextMenuItem
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                        >
                            <FileUp className="h-4 w-4" />
                            {uploading ? t("uploading") : t("uploadFile")}
                        </ContextMenuItem>
                    )}
                </ContextMenuContent>
            </ContextMenu>

            {/* Create Folder Dialog */}
            <Dialog open={createFolderOpen} onOpenChange={setCreateFolderOpen}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>{t("newFolder")}</DialogTitle>
                        <DialogDescription>{t("createFolderDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>{t("folderName")}</Label>
                            <Input
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                placeholder={t("folderNamePlaceholder")}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && newName.trim()) handleCreateFolder();
                                }}
                                autoFocus
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>{tc("description")}</Label>
                            <Textarea
                                value={newDesc}
                                onChange={(e) => setNewDesc(e.target.value)}
                                placeholder={t("optional")}
                                rows={2}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>{t("accessType")}</Label>
                            <Select value={newAccessType} onValueChange={setNewAccessType}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="public">
                                        <span className="flex items-center gap-2">
                                            <Globe className="h-3.5 w-3.5" /> {t("public")}
                                        </span>
                                    </SelectItem>
                                    <SelectItem value="restricted">
                                        <span className="flex items-center gap-2">
                                            <Lock className="h-3.5 w-3.5" /> {t("restricted")}
                                        </span>
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCreateFolderOpen(false)}>
                            {tc("cancel")}
                        </Button>
                        <Button onClick={handleCreateFolder} disabled={saving || !newName.trim()}>
                            {saving ? t("saving") : tc("create")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation */}
            <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {deleteTarget?.type === "folder" ? t("deleteFolderTitle") : t("deleteDocTitle")}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {deleteTarget?.type === "folder" ? t("deleteFolderDesc") : t("deleteDocDesc")}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
                        <AlertDialogAction onClick={handleDeleteConfirm}>
                            {tc("delete")}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Toggle Access Confirmation */}
            <AlertDialog open={!!toggleAccessTarget} onOpenChange={(open) => !open && setToggleAccessTarget(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {toggleAccessTarget?.currentAccess === "public"
                                ? t("setRestrictedTitle")
                                : t("setPublicTitle")}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {toggleAccessTarget?.currentAccess === "public"
                                ? t("setRestrictedDesc")
                                : t("setPublicDesc")}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
                        <AlertDialogAction onClick={handleToggleAccess}>
                            {tc("confirm")}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Document Preview */}
            <DocumentPreview
                documentId={previewDocId}
                documentName={previewDocName}
                onClose={() => setPreviewDocId(null)}
            />
        </>
    );
}
