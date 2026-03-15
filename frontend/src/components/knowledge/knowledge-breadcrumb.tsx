"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { ChevronRight, Home } from "lucide-react";
import type { KnowledgeFolder } from "@/types/models";

interface KnowledgeBreadcrumbProps {
    folders: KnowledgeFolder[];
    currentFolderId: string | null;
    onNavigate: (folderId: string | null) => void;
}

/** Build path from root to current folder. */
function buildPath(folders: KnowledgeFolder[], targetId: string | null): KnowledgeFolder[] {
    if (!targetId) return [];
    const map = new Map(folders.map((f) => [f.id, f]));
    const path: KnowledgeFolder[] = [];
    let current = map.get(targetId);
    while (current) {
        path.unshift(current);
        current = current.parent_id ? map.get(current.parent_id) : undefined;
    }
    return path;
}

export function KnowledgeBreadcrumb({ folders, currentFolderId, onNavigate }: KnowledgeBreadcrumbProps) {
    const t = useTranslations("tenant");
    const path = useMemo(() => buildPath(folders, currentFolderId), [folders, currentFolderId]);

    return (
        <nav className="flex items-center gap-1 text-sm min-h-[28px]">
            <button
                onClick={() => onNavigate(null)}
                className="flex items-center gap-1 px-2 py-1 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            >
                <Home className="h-3.5 w-3.5" />
                <span>{t("knowledgeTitle")}</span>
            </button>
            {path.map((folder) => (
                <div key={folder.id} className="flex items-center gap-1">
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    <button
                        onClick={() => onNavigate(folder.id)}
                        className={`px-2 py-1 rounded-md transition-colors ${
                            folder.id === currentFolderId
                                ? "font-medium text-foreground"
                                : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`}
                    >
                        {folder.name}
                    </button>
                </div>
            ))}
        </nav>
    );
}
