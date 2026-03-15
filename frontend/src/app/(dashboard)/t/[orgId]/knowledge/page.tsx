"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { PageHeader } from "@/components/shared/page-header";
import { PermissionGate } from "@/components/shared/permission-gate";
import { KnowledgeBreadcrumb } from "@/components/knowledge/knowledge-breadcrumb";
import { KnowledgeGrid } from "@/components/knowledge/knowledge-grid";
import { FolderAccessTab } from "@/components/knowledge/folder-access-tab";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Settings } from "lucide-react";
import { fetchFolders } from "@/lib/api/knowledge";
import { useCurrentOrg } from "@/contexts/org-context";
import type { KnowledgeFolder } from "@/types/models";

export default function TenantKnowledgePage() {
    const t = useTranslations("tenant");
    const { orgId } = useCurrentOrg();
    const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
    const [permissionsOpen, setPermissionsOpen] = useState(false);

    const { data: folders, mutate: mutateFolders } = useSWR(
        orgId ? ["knowledge-folders", orgId] : null,
        fetchFolders,
    );

    const currentFolder = folders?.find((f) => f.id === currentFolderId) ?? null;

    const navigateTo = useCallback((folderId: string | null) => {
        setCurrentFolderId(folderId);
    }, []);

    return (
        <PermissionGate permission="folder.view" pageLevel>
            <div className="space-y-4">
                <PageHeader title={t("knowledgeTitle")} description={t("knowledgeDesc")} />

                {/* Breadcrumb + Toolbar */}
                <div className="flex items-center justify-between gap-4">
                    <KnowledgeBreadcrumb
                        folders={folders || []}
                        currentFolderId={currentFolderId}
                        onNavigate={navigateTo}
                    />
                    {currentFolder && (
                        <PermissionGate permission="folder_access.manage">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setPermissionsOpen(true)}
                            >
                                <Settings className="h-4 w-4 mr-1" />
                                {t("folderPermissions")}
                            </Button>
                        </PermissionGate>
                    )}
                </div>

                {/* Grid */}
                <KnowledgeGrid
                    folders={folders || []}
                    currentFolderId={currentFolderId}
                    onOpenFolder={navigateTo}
                    onMutateFolders={mutateFolders}
                />

                {/* Folder Permissions Dialog */}
                {currentFolder && (
                    <Dialog open={permissionsOpen} onOpenChange={setPermissionsOpen}>
                        <DialogContent className="max-w-lg">
                            <DialogHeader>
                                <DialogTitle>
                                    {t("folderPermissions")} — {currentFolder.name}
                                </DialogTitle>
                            </DialogHeader>
                            <FolderAccessTab
                                folderId={currentFolder.id}
                                accessType={currentFolder.access_type}
                                onMutate={mutateFolders}
                            />
                        </DialogContent>
                    </Dialog>
                )}
            </div>
        </PermissionGate>
    );
}
