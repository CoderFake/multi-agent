/**
 * Notification API functions — list, count, mark read.
 * Rule 4: API functions in lib/api/, types from types/models.
 */
import { api } from "@/lib/api-client";
import type { NotificationListResponse } from "@/types/models";

export function fetchNotifications(page = 1, pageSize = 10) {
    return api.get<NotificationListResponse>(
        `/tenant/notifications?page=${page}&page_size=${pageSize}`,
    );
}

export function fetchUnreadCount() {
    return api.get<{ unread_count: number }>("/tenant/notifications/count");
}

export function markNotificationRead(id: string) {
    return api.put<{ success: boolean }>(`/tenant/notifications/${id}/read`);
}

export function markAllNotificationsRead() {
    return api.put<{ marked_count: number }>("/tenant/notifications/read-all");
}
