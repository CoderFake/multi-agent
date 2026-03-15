/**
 * Knowledge API — folders, documents, agent knowledge sources.
 * All calls use X-Org-Id header (auto-attached by api-client).
 */
import { api } from "@/lib/api-client";
import type {
    KnowledgeFolder,
    FolderCreate,
    FolderUpdate,
    KnowledgeDocument,
    FolderAccess,
    AgentKnowledgeSource,
    ActiveIndexJob,
} from "@/types/models";

// ── Folders ─────────────────────────────────────────────────────────────

export function fetchFolders() {
    return api.get<KnowledgeFolder[]>("/tenant/knowledge/folders");
}

export function createFolder(data: FolderCreate) {
    return api.post<KnowledgeFolder>("/tenant/knowledge/folders", data);
}

export function updateFolder(folderId: string, data: FolderUpdate) {
    return api.put<KnowledgeFolder>(`/tenant/knowledge/folders/${folderId}`, data);
}

export function deleteFolder(folderId: string) {
    return api.delete(`/tenant/knowledge/folders/${folderId}`);
}

// ── Folder Access ───────────────────────────────────────────────────────

export function fetchFolderAccess(folderId: string) {
    return api.get<FolderAccess[]>(`/tenant/knowledge/folders/${folderId}/access`);
}

export function setFolderAccess(folderId: string, groupId: string, canRead = true, canWrite = false) {
    return api.post(`/tenant/knowledge/folders/${folderId}/access`, {
        group_id: groupId,
        can_read: canRead,
        can_write: canWrite,
    });
}

export function removeFolderAccess(folderId: string, groupId: string) {
    return api.delete(`/tenant/knowledge/folders/${folderId}/access/${groupId}`);
}

/** Lightweight group list for folder access combobox (no group.view needed). */
export function fetchGroupsForAccess() {
    return api.get<{ id: string; name: string }[]>("/tenant/knowledge/folders/groups");
}

// ── Documents ───────────────────────────────────────────────────────────

export function fetchDocuments(folderId: string) {
    return api.get<KnowledgeDocument[]>(`/tenant/knowledge/folders/${folderId}/documents`);
}

export function uploadDocument(title: string, folderId: string, file: File) {
    const formData = new FormData();
    formData.append("title", title);
    formData.append("folder_id", folderId);
    formData.append("file", file);
    return api.postForm<KnowledgeDocument>("/tenant/knowledge/documents", formData);
}

export function deleteDocument(documentId: string) {
    return api.delete(`/tenant/knowledge/documents/${documentId}`);
}

export function fetchDocumentUrl(documentId: string) {
    return api.get<{ id: string; file_name: string; file_type: string; content_type: string; url: string }>(
        `/tenant/knowledge/documents/${documentId}/url`,
    );
}

// ── Agent Knowledge Sources ─────────────────────────────────────────────

export function fetchAgentSources(agentId: string) {
    return api.get<AgentKnowledgeSource[]>(`/tenant/knowledge/agent-sources/${agentId}`);
}

export function addAgentSource(agentId: string, folderId?: string, documentId?: string) {
    return api.post<AgentKnowledgeSource>("/tenant/knowledge/agent-sources", {
        agent_id: agentId,
        folder_id: folderId || null,
        document_id: documentId || null,
    });
}

export function removeAgentSource(sourceId: string) {
    return api.delete(`/tenant/knowledge/agent-sources/${sourceId}`);
}

// ── Indexing ─────────────────────────────────────────────────────────────

export function fetchActiveTasks() {
    return api.get<ActiveIndexJob[]>(
        "/tenant/knowledge/indexing/tasks",
    );
}

export function submitIndexing(documentId: string, agentCode?: string) {
    return api.post<{ job_id: string; document_id: string; status: string }>(
        `/tenant/knowledge/indexing/documents/${documentId}/index`,
        agentCode ? { agent_code: agentCode } : {},
    );
}

export function syncJobStatus(jobId: string) {
    return api.post(`/tenant/knowledge/indexing/${jobId}/sync`, {});
}

