"use client";

/**
 * FeedbackDialog — submit platform feedback with optional images.
 * Rule 3: all text from i18n. Rule 4: API from lib/api/. Rule 5: SRP.
 */
import { useState, useRef } from "react";
import { useTranslations } from "next-intl";
import { MessageSquarePlus, ImagePlus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { submitFeedback } from "@/lib/api/feedback";
import { toast } from "sonner";

const CATEGORIES = ["bug", "feature_request", "question", "other"] as const;
const MAX_IMAGES = 5;

export function FeedbackDialog() {
    const t = useTranslations("feedback");
    const [open, setOpen] = useState(false);
    const [category, setCategory] = useState<string>("bug");
    const [message, setMessage] = useState("");
    const [images, setImages] = useState<File[]>([]);
    const [previews, setPreviews] = useState<string[]>([]);
    const [submitting, setSubmitting] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    const handleAddImages = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        const remaining = MAX_IMAGES - images.length;
        const newFiles = files.slice(0, remaining);

        setImages((prev) => [...prev, ...newFiles]);
        setPreviews((prev) => [
            ...prev,
            ...newFiles.map((f) => URL.createObjectURL(f)),
        ]);
    };

    const handleRemoveImage = (index: number) => {
        URL.revokeObjectURL(previews[index]);
        setImages((prev) => prev.filter((_, i) => i !== index));
        setPreviews((prev) => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async () => {
        if (!message.trim()) return;
        setSubmitting(true);
        try {
            await submitFeedback(category, message, images.length > 0 ? images : undefined);
            toast.success(t("submitSuccess"));
            setOpen(false);
            // Reset form
            setCategory("bug");
            setMessage("");
            previews.forEach(URL.revokeObjectURL);
            setImages([]);
            setPreviews([]);
        } catch {
            toast.error("Failed to submit feedback");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="w-full justify-start gap-2 px-2">
                    <MessageSquarePlus className="h-4 w-4" />
                    <span>{t("title")}</span>
                </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>{t("title")}</DialogTitle>
                    <DialogDescription>
                        {t("messagePlaceholder")}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Category */}
                    <div className="space-y-2">
                        <Label>{t("category")}</Label>
                        <div className="flex flex-wrap gap-2">
                            {CATEGORIES.map((cat) => (
                                <Button
                                    key={cat}
                                    type="button"
                                    variant={category === cat ? "default" : "outline"}
                                    size="sm"
                                    onClick={() => setCategory(cat)}
                                >
                                    {t(cat)}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* Message */}
                    <div className="space-y-2">
                        <Label>{t("message")}</Label>
                        <Textarea
                            placeholder={t("messagePlaceholder")}
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            rows={4}
                            maxLength={10000}
                        />
                    </div>

                    {/* Images */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label>{t("attachImages")}</Label>
                            <span className="text-xs text-muted-foreground">
                                {t("maxImages", { max: MAX_IMAGES })}
                            </span>
                        </div>

                        {/* Previews */}
                        {previews.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                                {previews.map((src, i) => (
                                    <div key={i} className="relative h-16 w-16 rounded-md overflow-hidden border">
                                        <img src={src} alt="" className="h-full w-full object-cover" />
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveImage(i)}
                                            className="absolute -right-1 -top-1 rounded-full bg-destructive p-0.5 text-destructive-foreground"
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {images.length < MAX_IMAGES && (
                            <>
                                <input
                                    ref={fileRef}
                                    type="file"
                                    accept="image/jpeg,image/png,image/gif,image/webp"
                                    multiple
                                    onChange={handleAddImages}
                                    className="hidden"
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => fileRef.current?.click()}
                                >
                                    <ImagePlus className="mr-2 h-4 w-4" />
                                    {t("attachImages")}
                                </Button>
                            </>
                        )}
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        onClick={handleSubmit}
                        disabled={submitting || !message.trim()}
                    >
                        {submitting ? t("submitting") : t("submit")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
