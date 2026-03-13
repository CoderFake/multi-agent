"use client";

import type { ReactNode } from "react";
import { usePermissions } from "@/hooks/use-permissions";
import { useCurrentOrg } from "@/contexts/org-context";

interface PermissionGateProps {
    /** Permission codename, e.g. "agent.view" */
    permission: string;
    /** Content to show when permission is granted */
    children: ReactNode;
    /** Optional fallback when permission is denied */
    fallback?: ReactNode;
}

/**
 * Conditionally renders children based on current user's permissions.
 * - Superusers always pass.
 * - Shows nothing (or fallback) while loading to avoid flash of "denied".
 */
export function PermissionGate({
    permission,
    children,
    fallback = null,
}: PermissionGateProps) {
    const { hasPermission, isLoading } = usePermissions();
    const { isSuperuser } = useCurrentOrg();

    // Loading guard — don't deny while permissions are loading
    if (isLoading) return null;

    // Superuser bypass
    if (isSuperuser) return <>{children}</>;

    // Check permission
    if (hasPermission(permission)) return <>{children}</>;

    return <>{fallback}</>;
}
