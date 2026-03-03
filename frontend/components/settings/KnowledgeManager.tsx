'use client';

import { useState, useEffect, useRef } from 'react';
import { Upload, Trash2, FileText, Loader2, RefreshCw, CheckCircle, Clock, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

interface KnowledgeDoc {
    doc_id: string;
    file_name: string;
    status: 'processing' | 'completed' | 'failed';
    engine: string;
    page_count: number;
    created_at: string;
}

const STATUS_ICON: Record<string, React.ReactNode> = {
    completed: <CheckCircle className="h-4 w-4 text-green-500" />,
    processing: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
};

const ENGINE_BADGE: Record<string, string> = {
    'hybrid/docling': 'Docling',
    'hybrid/paddleocr': 'PP-OCRv5',
    'docling': 'Docling',
    'paddleocr': 'PP-OCRv5',
    'hybrid': 'Hybrid',
};

export function KnowledgeManager() {
    const { getIdToken } = useAuth();
    const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const fetchDocs = async () => {
        setLoading(true);
        try {
            const token = await getIdToken();
            if (!token) return;
            const data = await api.listKnowledgeDocs(token);
            setDocs(data);
        } catch (e) {
            console.error('Failed to list knowledge docs:', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchDocs(); }, []);

    const handleUpload = async (files: FileList | null) => {
        if (!files?.length) return;
        setUploading(true);
        try {
            const token = await getIdToken();
            if (!token) return;
            for (const file of Array.from(files)) {
                await api.uploadKnowledgeDoc(file, token);
            }
            await fetchDocs();
        } catch (e) {
            console.error('Upload failed:', e);
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (doc_id: string) => {
        try {
            const token = await getIdToken();
            if (!token) return;
            await api.deleteKnowledgeDoc(doc_id, token);
            setDocs(docs.filter(d => d.doc_id !== doc_id));
        } catch (e) {
            console.error('Delete failed:', e);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-base font-semibold mb-1">Knowledge Base</h3>
                <p className="text-sm text-muted-foreground">
                    Documents uploaded here are indexed into the agent's long-term knowledge (Milvus).
                    The agent searches these automatically when Research mode is enabled.
                </p>
            </div>

            {/* Upload zone */}
            <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                    dragOver ? 'border-[#6766FC] bg-[#f0f0ff]' : 'border-gray-200 hover:border-gray-300'
                }`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); }}
            >
                <div className="flex flex-col items-center gap-3">
                    {uploading ? (
                        <Loader2 className="h-8 w-8 text-[#6766FC] animate-spin" />
                    ) : (
                        <Upload className="h-8 w-8 text-gray-400" />
                    )}
                    <div>
                        <p className="text-sm font-medium">
                            {uploading ? 'Uploading…' : 'Drop files here or'}
                        </p>
                        {!uploading && (
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className="text-sm text-[#6766FC] hover:underline"
                            >
                                browse files
                            </button>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                            PDF, DOCX, PPTX, XLSX, HTML, Images
                        </p>
                    </div>
                </div>
                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    multiple
                    accept=".pdf,.docx,.pptx,.xlsx,.html,.htm,.png,.jpg,.jpeg,.tiff"
                    onChange={(e) => handleUpload(e.target.files)}
                />
            </div>

            {/* Document list */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-muted-foreground">
                        {docs.length} document{docs.length !== 1 ? 's' : ''}
                    </span>
                    <button
                        onClick={fetchDocs}
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                        <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                {docs.length === 0 && !loading && (
                    <div className="text-center py-8 text-sm text-muted-foreground">
                        No documents in knowledge base yet
                    </div>
                )}

                {docs.map((doc) => (
                    <div
                        key={doc.doc_id}
                        className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
                    >
                        <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{doc.file_name}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-xs text-muted-foreground">
                                    {ENGINE_BADGE[doc.engine] ?? doc.engine}
                                </span>
                                {doc.page_count > 0 && (
                                    <span className="text-xs text-muted-foreground">· {doc.page_count}p</span>
                                )}
                                <span className="text-xs text-muted-foreground">
                                    · {new Date(doc.created_at).toLocaleDateString()}
                                </span>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {STATUS_ICON[doc.status] ?? <Clock className="h-4 w-4 text-gray-400" />}
                            <button
                                onClick={() => handleDelete(doc.doc_id)}
                                className="p-1 rounded hover:bg-red-50 hover:text-red-500 text-gray-400 transition-colors"
                                title="Delete"
                            >
                                <Trash2 className="h-4 w-4" />
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
