/**
 * Hook to show error toast with translated message from backend error codes.
 * Maps ApiError.error_code → i18n "errors" namespace → localized toast.
 */
import { useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import type { ApiError } from "@/lib/api-client";

export function useErrorToast() {
    const te = useTranslations("errors");
    const tc = useTranslations("common");

    /**
     * Show error toast with translated message.
     * Falls back to `detail` from backend, then generic "error".
     */
    const showError = useCallback(
        (err: unknown) => {
            const apiErr = err as ApiError;
            const code = apiErr?.error_code;

            // Try translated error code first
            if (code && te.has(code)) {
                toast.error(te(code));
                return;
            }

            // Fallback: backend detail message
            if (apiErr?.detail) {
                toast.error(apiErr.detail);
                return;
            }

            // Last resort: generic
            toast.error(tc("error"));
        },
        [te, tc],
    );

    return { showError };
}
