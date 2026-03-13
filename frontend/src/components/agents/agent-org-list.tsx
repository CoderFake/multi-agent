"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import type { AgentOrgItem, OrganizationListItem } from "@/types/models";
import { fetchAgentOrgs, setAgentOrgs, fetchOrganizations } from "@/lib/api/system";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Building2, Check } from "lucide-react";

interface AgentOrgListProps {
  agentId: string;
  isPublic: boolean;
}

export function AgentOrgList({ agentId, isPublic }: AgentOrgListProps) {
  const ts = useTranslations("system");
  const t = useTranslations("common");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Fetch all orgs for the checkbox list
  const { data: orgPage } = useSWR(
    "all-orgs-for-agent",
    () => fetchOrganizations({ page: 1, pageSize: 200 }),
  );
  const allOrgs = orgPage?.items ?? [];

  // Fetch assigned orgs for this agent
  const { data: assignedOrgs, mutate: mutateAssigned } = useSWR<AgentOrgItem[]>(
    agentId ? `agent-orgs-${agentId}` : null,
    () => fetchAgentOrgs(agentId),
  );

  // Sync selected IDs when assigned orgs data loads
  useEffect(() => {
    if (assignedOrgs) {
      setSelectedIds(new Set(assignedOrgs.map((o) => o.org_id)));
      setDirty(false);
    }
  }, [assignedOrgs]);

  if (isPublic) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground text-sm gap-2">
        <Building2 className="h-8 w-8 opacity-40" />
        <span className="text-center">{ts("allOrgsAssigned")}</span>
      </div>
    );
  }

  const toggleOrg = (orgId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(orgId)) {
        next.delete(orgId);
      } else {
        next.add(orgId);
      }
      return next;
    });
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await setAgentOrgs(agentId, Array.from(selectedIds));
      await mutateAssigned();
      setDirty(false);
      toast.success(t("updateSuccess"));
    } catch {
      toast.error("Error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="max-h-[340px] overflow-y-auto space-y-1 pr-1">
        {allOrgs.length === 0 ? (
          <div className="text-sm text-muted-foreground py-4 text-center">
            {ts("noOrgsAssigned")}
          </div>
        ) : (
          allOrgs.map((org: OrganizationListItem) => {
            const active = selectedIds.has(org.id);
            return (
              <button
                key={org.id}
                type="button"
                onClick={() => toggleOrg(org.id)}
                className={`w-full flex items-center gap-3 rounded-lg border p-2.5 text-left transition-colors ${
                  active
                    ? "border-primary/50 bg-primary/5"
                    : "border-transparent hover:bg-muted/50"
                }`}
              >
                <div
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-muted-foreground/30"
                  }`}
                >
                  {active && <Check className="h-3 w-3" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm truncate">{org.name}</div>
                  {org.subdomain && (
                    <div className="text-xs text-muted-foreground truncate">
                      {org.subdomain}
                    </div>
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>

      {dirty && (
        <Button
          onClick={handleSave}
          disabled={saving}
          size="sm"
          className="w-full"
        >
          {saving ? t("processing") : ts("saveOrgAssignment")}
        </Button>
      )}
    </div>
  );
}
