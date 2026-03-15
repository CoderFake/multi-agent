"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, Download, ExternalLink } from "lucide-react";
import { fetchDocumentUrl } from "@/lib/api/knowledge";

interface DocumentPreviewProps {
    documentId: string | null;
    documentName: string;
    onClose: () => void;
}

const IMAGE_TYPES = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg"]);
const PDF_TYPES = new Set(["pdf"]);

export function DocumentPreview({ documentId, documentName, onClose }: DocumentPreviewProps) {
    const t = useTranslations("tenant");
    const [loading, setLoading] = useState(false);
    const [docData, setDocData] = useState<{
        url: string; file_type: string; file_name: string;
    } | null>(null);

    const load = useCallback(async () => {
        if (!documentId) return;
        setLoading(true);
        try {
            const result = await fetchDocumentUrl(documentId);
            setDocData(result);
        } catch {
            toast.error(t("docPreviewFailed"));
            onClose();
        } finally {
            setLoading(false);
        }
    }, [documentId, onClose, t]);

    // Load on open
    if (documentId && !docData && !loading) {
        load();
    }

    const isImage = docData ? IMAGE_TYPES.has(docData.file_type) : false;
    const isPdf = docData ? PDF_TYPES.has(docData.file_type) : false;

    return (
        <Dialog open={!!documentId} onOpenChange={(open) => {
            if (!open) {
                setDocData(null);
                onClose();
            }
        }}>
            <DialogContent className="max-w-5xl w-[95vw] h-[90vh] flex flex-col p-0 gap-0">
                {/* Header */}
                <DialogHeader className="shrink-0 px-6 py-4 border-b border-border flex flex-row items-center justify-between">
                    <DialogTitle className="text-base truncate flex-1 mr-4">
                        {docData?.file_name || documentName}
                    </DialogTitle>
                    <div className="flex items-center gap-2 shrink-0 mr-8">
                        {docData && (
                            <>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => window.open(docData.url, "_blank")}
                                >
                                    <ExternalLink className="h-4 w-4 mr-1" />
                                    {t("openInNewTab")}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    asChild
                                >
                                    <a href={docData.url} download={docData.file_name}>
                                        <Download className="h-4 w-4 mr-1" />
                                        {t("download")}
                                    </a>
                                </Button>
                            </>
                        )}
                    </div>
                </DialogHeader>

                {/* Content */}
                <div className="flex-1 min-h-0 overflow-auto bg-muted/30">
                    {loading ? (
                        <div className="flex items-center justify-center h-full">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : docData ? (
                        <>
                            {isImage && (
                                <div className="flex items-center justify-center h-full p-4">
                                    <img
                                        src={docData.url}
                                        alt={docData.file_name}
                                        className="max-w-full max-h-full object-contain rounded-lg"
                                    />
                                </div>
                            )}
                            {isPdf && (
                                <iframe
                                    src={docData.url}
                                    className="w-full h-full border-0"
                                    title={docData.file_name}
                                />
                            )}
                            {!isImage && !isPdf && (
                                <div className="flex flex-col items-center justify-center h-full gap-4 text-muted-foreground">
                                    <p className="text-sm">{t("previewNotSupported")}</p>
                                    <Button asChild>
                                        <a href={docData.url} download={docData.file_name}>
                                            <Download className="h-4 w-4 mr-2" />
                                            {t("download")}
                                        </a>
                                    </Button>
                                </div>
                            )}
                        </>
                    ) : null}
                </div>
            </DialogContent>
        </Dialog>
    );
}
