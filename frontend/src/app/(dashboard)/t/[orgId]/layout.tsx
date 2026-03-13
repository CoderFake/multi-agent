"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useCurrentOrg } from "@/contexts/org-context";

/**
 * Tenant layout — syncs orgId from URL params to OrgContext.
 * Route: /t/[orgId]/...
 */
export default function TenantLayout({ children }: { children: React.ReactNode }) {
    const params = useParams();
    const { orgId, switchOrg } = useCurrentOrg();
    const urlOrgId = params.orgId as string;

    // Sync URL org to context
    useEffect(() => {
        if (urlOrgId && urlOrgId !== orgId) {
            switchOrg(urlOrgId);
        }
    }, [urlOrgId, orgId, switchOrg]);

    return <>{children}</>;
}
