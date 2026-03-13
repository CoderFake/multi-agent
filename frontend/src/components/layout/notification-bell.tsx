"use client";

/**
 * NotificationBell — bell icon + badge + dropdown in TopBar.
 * Rule 3: all text from i18n. Rule 4: API from lib/api/. Rule 5: SRP.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Bell, CheckCheck } from "lucide-react";
import { useCurrentOrg } from "@/contexts/org-context";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    fetchNotifications,
    fetchUnreadCount,
    markNotificationRead,
    markAllNotificationsRead,
} from "@/lib/api/notifications";
import type { Notification } from "@/types/models";

const POLL_INTERVAL = 30_000; // 30 seconds

/** Resolve notification code to locale string with data interpolation. */
function useNotificationText(notification: Notification) {
    const t = useTranslations("notification");

    // title_code = "notification.invite_accepted" → key = "invite_accepted"
    const titleKey = notification.title_code.replace("notification.", "");
    const messageKey = notification.message_code
        ? notification.message_code.replace("notification.", "")
        : null;

    const title = t(titleKey, notification.data ?? {});
    const message = messageKey ? t(messageKey, notification.data ?? {}) : null;

    return { title, message };
}

function NotificationItem({
    notification,
    onMarkRead,
}: {
    notification: Notification;
    onMarkRead: (id: string) => void;
}) {
    const { title, message } = useNotificationText(notification);
    const t = useTranslations("notification");

    const getTimeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime();
        const mins = Math.floor(diff / 60_000);
        if (mins < 1) return t("justNow");
        if (mins < 60) return t("minutesAgo", { count: mins });
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return t("hoursAgo", { count: hrs });
        return t("daysAgo", { count: Math.floor(hrs / 24) });
    };

    return (
        <DropdownMenuItem
            className={`flex flex-col items-start gap-1 p-3 cursor-pointer ${!notification.is_read ? "bg-accent/50" : ""
                }`}
            onClick={() => {
                if (!notification.is_read) onMarkRead(notification.id);
            }}
        >
            <div className="flex w-full items-center justify-between gap-2">
                <span className="text-sm font-medium">{title}</span>
                {!notification.is_read && (
                    <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
                )}
            </div>
            {message && (
                <span className="text-xs text-muted-foreground line-clamp-2">
                    {message}
                </span>
            )}
            <span className="text-[10px] text-muted-foreground/70">
                {getTimeAgo(notification.created_at)}
            </span>
        </DropdownMenuItem>
    );
}

export function NotificationBell() {
    const t = useTranslations("notification");
    const { orgId } = useCurrentOrg();
    const [unreadCount, setUnreadCount] = useState(0);
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [open, setOpen] = useState(false);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const pollUnread = useCallback(async () => {
        if (!orgId) return; // skip when no org selected
        try {
            const data = await fetchUnreadCount();
            setUnreadCount(data.unread_count);
        } catch {
            // silent — org may have been deselected
        }
    }, [orgId]);

    // Poll unread count — only when org is selected
    useEffect(() => {
        if (!orgId) {
            setUnreadCount(0);
            setNotifications([]);
            return;
        }
        pollUnread();
        intervalRef.current = setInterval(pollUnread, POLL_INTERVAL);
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [pollUnread, orgId]);

    // Load notifications when dropdown opens
    const handleOpen = useCallback(
        async (isOpen: boolean) => {
            setOpen(isOpen);
            if (isOpen && orgId) {
                try {
                    const data = await fetchNotifications(1, 8);
                    setNotifications(data.items);
                    setUnreadCount(data.unread_count);
                } catch {
                    // silent
                }
            }
        },
        [orgId],
    );

    const handleMarkRead = useCallback(async (id: string) => {
        try {
            await markNotificationRead(id);
            setNotifications((prev) =>
                prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
            );
            setUnreadCount((c) => Math.max(0, c - 1));
        } catch {
            // silent
        }
    }, []);

    const handleMarkAllRead = useCallback(async () => {
        try {
            await markAllNotificationsRead();
            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
            setUnreadCount(0);
        } catch {
            // silent
        }
    }, []);

    return (
        <DropdownMenu open={open} onOpenChange={handleOpen}>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative h-8 w-8">
                    <Bell className="h-4 w-4" />
                    {unreadCount > 0 && (
                        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
                            {unreadCount > 99 ? "99+" : unreadCount}
                        </span>
                    )}
                </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-80">
                {/* Header */}
                <div className="flex items-center justify-between px-3 py-2">
                    <span className="text-sm font-semibold">{t("title")}</span>
                    {unreadCount > 0 && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-auto px-2 py-1 text-xs"
                            onClick={(e) => {
                                e.preventDefault();
                                handleMarkAllRead();
                            }}
                        >
                            <CheckCheck className="mr-1 h-3 w-3" />
                            {t("markAllRead")}
                        </Button>
                    )}
                </div>
                <DropdownMenuSeparator />

                {/* Items */}
                {notifications.length === 0 ? (
                    <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                        {t("noNotifications")}
                    </div>
                ) : (
                    <div className="max-h-80 overflow-y-auto">
                        {notifications.map((n) => (
                            <NotificationItem
                                key={n.id}
                                notification={n}
                                onMarkRead={handleMarkRead}
                            />
                        ))}
                    </div>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
