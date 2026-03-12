"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api-client";
import type { OrgMembership } from "@/types/auth";

interface OrgContextValue {
  /** Currently selected org */
  currentOrg: OrgMembership | null;
  /** All orgs the user belongs to */
  memberships: OrgMembership[];
  /** Switch to a different org */
  switchOrg: (orgId: string) => void;
  /** Current org_id shortcut */
  orgId: string | null;
  /** Current org_role shortcut */
  orgRole: string | null;
  /** Whether the user is a superuser */
  isSuperuser: boolean;
}

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

const ORG_STORAGE_KEY = "cms_current_org_id";

export function OrgProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [currentOrg, setCurrentOrg] = useState<OrgMembership | null>(null);

  const memberships = user?.memberships ?? [];
  const isSuperuser = user?.is_superuser ?? false;

  // Restore org from localStorage on mount / when user changes
  useEffect(() => {
    if (!user || memberships.length === 0) {
      setCurrentOrg(null);
      return;
    }

    const savedOrgId =
      typeof window !== "undefined"
        ? localStorage.getItem(ORG_STORAGE_KEY)
        : null;

    const saved = memberships.find((m) => m.org_id === savedOrgId);
    const selected = saved ?? memberships[0];
    setCurrentOrg(selected);
    // Sync api client so every request carries X-Org-Id
    api.setOrgId(selected.org_id);
  }, [user, memberships]);

  const switchOrg = useCallback(
    (orgId: string) => {
      const org = memberships.find((m) => m.org_id === orgId);
      if (org) {
        setCurrentOrg(org);
        api.setOrgId(org.org_id);
        localStorage.setItem(ORG_STORAGE_KEY, orgId);
      }
    },
    [memberships],
  );

  return (
    <OrgContext.Provider
      value={{
        currentOrg,
        memberships,
        switchOrg,
        orgId: currentOrg?.org_id ?? null,
        orgRole: currentOrg?.org_role ?? null,
        isSuperuser,
      }}
    >
      {children}
    </OrgContext.Provider>
  );
}

export function useCurrentOrg() {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error("useCurrentOrg must be used within OrgProvider");
  return ctx;
}
