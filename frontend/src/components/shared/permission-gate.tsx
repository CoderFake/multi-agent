"use client";

import type { ReactNode } from "react";
import { usePermissions } from "@/hooks/use-permissions";
import { useCurrentOrg } from "@/contexts/org-context";
import { AccessDenied } from "@/components/shared/access-denied";

interface PermissionGateProps {
    /** Permission codename, e.g. "agent.view" */
    permission: string;
    /** Content to show when permission is granted */
    children: ReactNode;
    /**
     * Optional fallback when permission is denied.
     * - Default: `null` (hides silently — safe for buttons/actions)
     * - Pass a ReactNode to show custom fallback
     * - Set `pageLevel` to show full 403 UI automatically
     */
    fallback?: ReactNode;
    /**
     * When true, shows a full 403 AccessDenied page when denied.
     * Use this for page-level gates wrapping entire pages/tabs.
     * Button-level gates should NOT use this.
     */
    pageLevel?: boolean;
}

/**
 * Conditionally renders children based on current user's permissions.
 * - Superusers always pass.
 * - Shows nothing while loading to avoid flash of "denied".
 *
 * For page-level usage (wrapping full pages):
 *   <PermissionGate permission="agent.view" pageLevel>
 *
 * For button-level usage (hiding buttons):
 *   <PermissionGate permission="agent.create">
 */
export function PermissionGate({
    permission,
    children,
    fallback,
    pageLevel = false,
}: PermissionGateProps) {
    const { hasPermission, isLoading } = usePermissions();
    const { isSuperuser } = useCurrentOrg();

    // Loading guard — don't deny while permissions are loading
    if (isLoading) return null;

    // Superuser bypass
    if (isSuperuser) return <>{children}</>;

    // Check permission
    if (hasPermission(permission)) return <>{children}</>;

    // Denied — explicit fallback takes precedence
    if (fallback !== undefined) return <>{fallback}</>;

    // Page-level gate → show 403 UI
    if (pageLevel) return <AccessDenied permission={permission} />;

    // Button-level gate → hide silently
    return null;
}
