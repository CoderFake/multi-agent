/**
 * Feedback API functions — submit, list (superuser), update status.
 * Rule 4: API functions in lib/api/, types from types/models.
 */
import { api } from "@/lib/api-client";
import type { FeedbackListResponse } from "@/types/models";

/** Submit feedback with optional images (multipart/form-data). */
export function submitFeedback(category: string, message: string, images?: File[]) {
    const formData = new FormData();
    formData.append("category", category);
    formData.append("message", message);
    if (images) {
        images.forEach((file) => formData.append("images", file));
    }
    return api.postForm<{ id: string; category: string; status: string }>(
        "/feedback",
        formData,
    );
}

/** List all feedback — superuser only. */
export function fetchFeedbackList(
    status?: string,
    page = 1,
    pageSize = 20,
) {
    const statusParam = status ? `&status=${status}` : "";
    return api.get<FeedbackListResponse>(
        `/feedback?page=${page}&page_size=${pageSize}${statusParam}`,
    );
}

/** Update feedback status — superuser only. */
export function updateFeedbackStatus(id: string, status: string) {
    return api.put<{ id: string; status: string }>(
        `/feedback/${id}/status`,
        { status },
    );
}
