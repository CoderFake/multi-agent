"use client";

import { useEffect, useState, useCallback } from "react";
import { fetchUIPermissions } from "@/lib/api/permissions";
import { useCurrentOrg } from "@/contexts/org-context";
import type { UIPermissions } from "@/types/models";

/**
 * Hook to load and check permissions for the current user in the current org.
 * Calls GET /permissions/me whenever org changes.
 */
export function usePermissions() {
  const { orgId } = useCurrentOrg();
  const [permissions, setPermissions] = useState<UIPermissions | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!orgId) {
      setPermissions(null);
      return;
    }

    setIsLoading(true);
    fetchUIPermissions()
      .then(setPermissions)
      .catch(() => setPermissions(null))
      .finally(() => setIsLoading(false));
  }, [orgId]);

  const hasPermission = useCallback(
    (codename: string): boolean => {
      if (!permissions) return false;
      // codename format: "resource.action" e.g. "agent.view"
      const parts = codename.split(".");
      if (parts.length === 2) {
        const [resource, action] = parts;
        return permissions.actions[resource]?.includes(action) ?? false;
      }
      return false;
    },
    [permissions],
  );

  const canView = useCallback(
    (resource: string): boolean => {
      return permissions?.nav_items.includes(resource) ?? false;
    },
    [permissions],
  );

  return {
    permissions,
    isLoading,
    hasPermission,
    canView,
    navItems: permissions?.nav_items ?? [],
    actions: permissions?.actions ?? {},
  };
}
