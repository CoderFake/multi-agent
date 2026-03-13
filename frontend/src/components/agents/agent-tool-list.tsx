"use client";

import { useTranslations } from "next-intl";
import useSWR from "swr";
import type { AgentToolItem } from "@/types/models";
import { fetchAgentTools } from "@/lib/api/system";
import { Wrench } from "lucide-react";

interface AgentToolListProps {
  agentId: string;
}

export function AgentToolList({ agentId }: AgentToolListProps) {
  const ts = useTranslations("system");

  const { data: tools, isLoading } = useSWR<AgentToolItem[]>(
    agentId ? `agent-tools-${agentId}` : null,
    () => fetchAgentTools(agentId),
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
        Loading...
      </div>
    );
  }

  if (!tools || tools.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground text-sm gap-2">
        <Wrench className="h-8 w-8 opacity-40" />
        <span>{ts("noToolsAssigned")}</span>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
      {tools.map((tool) => (
        <div
          key={tool.id}
          className="rounded-lg border bg-card p-3 space-y-1"
        >
          <div className="flex items-center gap-2">
            <Wrench className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <span className="font-medium text-sm">{tool.display_name}</span>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {tool.description ?? "—"}
          </p>
          <div className="flex items-center gap-2 text-xs">
            <code className="bg-muted px-1.5 py-0.5 rounded text-[10px]">
              {tool.codename}
            </code>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground">{tool.server_name}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
