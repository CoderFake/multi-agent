"use client";

import type { ReactNode } from "react";
import { usePermissions } from "@/hooks/use-permissions";
import { useCurrentOrg } from "@/contexts/org-context";

interface PermissionGateProps {
  /** Permission codename e.g. "agent.view", "user.create" */
  permission?: string;
  /** Allow superusers to bypass permission check */
  superuserOnly?: boolean;
  /** Fallback UI when denied */
  fallback?: ReactNode;
  /** Content to show while loading permissions (defaults to null) */
  loading?: ReactNode;
  children: ReactNode;
}

/**
 * Conditionally renders children based on user permissions.
 * Shows nothing (or `loading` prop) while permissions are loading to prevent
 * flash of denied content.
 *
 * Usage:
 *   <PermissionGate permission="agent.view">
 *     <AgentPage />
 *   </PermissionGate>
 *
 *   <PermissionGate superuserOnly>
 *     <SystemAdminPanel />
 *   </PermissionGate>
 */
export function PermissionGate({
  permission,
  superuserOnly = false,
  fallback = null,
  loading = null,
  children,
}: PermissionGateProps) {
  const { hasPermission, isLoading } = usePermissions();
  const { isSuperuser } = useCurrentOrg();

  // Superuser-only gate does not need to wait for permissions API
  if (superuserOnly) {
    return isSuperuser ? <>{children}</> : <>{fallback}</>;
  }

  // Wait for permissions to load before deciding — prevents flash denied
  if (isLoading) {
    return <>{loading}</>;
  }

  // Superusers bypass all permission checks
  if (isSuperuser) {
    return <>{children}</>;
  }

  if (permission && !hasPermission(permission)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
