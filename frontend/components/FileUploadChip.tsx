'use client';

import { X, FileText, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UploadedDoc } from '@/types/chat';

interface FileUploadChipProps {
    doc: UploadedDoc;
    onRemove: (doc_id: string) => void;
}

const ENGINE_SHORT: Record<string, string> = {
    'hybrid/docling': 'Docling',
    'hybrid/paddleocr': 'PP-OCRv5',
    'docling': 'Docling',
    'paddleocr': 'PP-OCRv5',
};

export function FileUploadChip({ doc, onRemove }: FileUploadChipProps) {
    const isLoading = doc.status === 'uploading' || doc.status === 'processing';
    const isFailed = doc.status === 'failed';

    return (
        <div
            className={cn(
                'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium border',
                'transition-colors max-w-[200px]',
                isFailed
                    ? 'bg-red-50 border-red-200 text-red-700'
                    : isLoading
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : 'bg-[#f0f0ff] border-[#d4d3ff] text-[#4f4ee8]'
            )}
        >
            {/* Icon */}
            {isLoading ? (
                <Loader2 className="h-3 w-3 animate-spin flex-shrink-0" />
            ) : isFailed ? (
                <XCircle className="h-3 w-3 flex-shrink-0" />
            ) : (
                <FileText className="h-3 w-3 flex-shrink-0" />
            )}

            {/* File name */}
            <span className="truncate max-w-[120px]">{doc.file_name}</span>

            {/* Engine badge */}
            {doc.engine && !isLoading && (
                <span className="text-[10px] opacity-60 flex-shrink-0">
                    {ENGINE_SHORT[doc.engine] ?? doc.engine}
                </span>
            )}

            {/* Status text */}
            {isLoading && (
                <span className="text-[10px] opacity-70 flex-shrink-0">
                    {doc.status === 'uploading' ? 'uploading…' : 'processing…'}
                </span>
            )}

            {/* Remove */}
            {!isLoading && (
                <button
                    onClick={() => onRemove(doc.doc_id)}
                    className="flex-shrink-0 hover:opacity-70 transition-opacity"
                    type="button"
                >
                    <X className="h-3 w-3" />
                </button>
            )}
        </div>
    );
}
