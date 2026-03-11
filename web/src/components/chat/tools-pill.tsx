"use client";

import { useEffect, useState } from "react";
import { ChevronDownIcon, SearchIcon, DatabaseIcon, WrenchIcon, GitMergeIcon, BotIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
} from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type Agent = {
  id: string;
  name: string;
  description: string;
  icon: string;
};

type ToolsPillProps = {
  className?: string;
  /** Controlled open state */
  isOpen?: boolean;
  /** Called when open state changes */
  onOpenChange?: (open: boolean) => void;
};

const iconMap: Record<string, React.ElementType> = {
  search: SearchIcon,
  database: DatabaseIcon,
  "file-text": WrenchIcon,
  "git-merge": GitMergeIcon,
  bot: BotIcon,
};

function loadEnabledConfig(agents: Agent[]): Record<string, boolean> {
  const saved = localStorage.getItem("enabled_agents");
  if (saved) return JSON.parse(saved);
  const defaults: Record<string, boolean> = {};
  agents.forEach((a) => (defaults[a.id] = true));
  return defaults;
}

export function ToolsPill({ className, isOpen, onOpenChange }: ToolsPillProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [enabledAgents, setEnabledAgents] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchAgents() {
      try {
        const response = await fetch("/api/agents");
        if (!response.ok) return;
        const data: Agent[] = await response.json();
        const config = loadEnabledConfig(data);
        setAgents(data);
        setEnabledAgents(config);
      } catch {
        // silently fail
      } finally {
        setIsLoading(false);
      }
    }

    fetchAgents();

    // Re-sync when settings dialog changes config
    window.addEventListener("agent-config-changed", fetchAgents);
    return () => window.removeEventListener("agent-config-changed", fetchAgents);
  }, []);

  const handleToggle = (id: string, checked: boolean) => {
    const newConfig = { ...enabledAgents, [id]: checked };
    setEnabledAgents(newConfig);
    localStorage.setItem("enabled_agents", JSON.stringify(newConfig));
    window.dispatchEvent(new Event("agent-config-changed"));
  };

  const enabledCount = agents.filter((a) => enabledAgents[a.id] !== false).length;

  if (isLoading || agents.length === 0) return null;

  return (
    <DropdownMenu open={isOpen} onOpenChange={onOpenChange}>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            "group inline-flex items-center gap-1.5 rounded-full",
            "border border-border/60 bg-background/80 backdrop-blur-sm",
            "px-3 py-1.5 text-sm text-muted-foreground",
            "transition-all duration-200 ease-out",
            "hover:border-border hover:bg-accent/50 hover:text-foreground",
            "focus-visible:outline-none",
            "active:scale-[0.96]",
            "data-[state=open]:scale-[0.96] data-[state=open]:border-border data-[state=open]:bg-accent/50 data-[state=open]:text-foreground",
            "disabled:pointer-events-none disabled:opacity-40",
            className,
          )}
        >
          <BotIcon className="size-3.5 transition-transform duration-200 group-hover:scale-110 group-data-[state=open]:scale-110" />
          <span className="font-medium">Agents</span>
          {/* Badge showing active count */}
          <span className={cn(
            "inline-flex items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none",
            "bg-primary/15 text-primary",
          )}>
            {enabledCount}/{agents.length}
          </span>
          <ChevronDownIcon className="size-3 opacity-50 transition-all duration-200 group-hover:rotate-90 group-hover:opacity-80 group-data-[state=open]:rotate-180 group-data-[state=open]:opacity-80" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="start"
        side="top"
        sideOffset={8}
        className="min-w-[260px] border-border/40 bg-popover/95 shadow-xl backdrop-blur-md"
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <div className="px-3 py-2 text-xs font-medium tracking-wide text-muted-foreground/70">
          Sub-Agents
        </div>

        <div className="space-y-0.5 px-1.5 pb-1.5">
          {agents.map((agent) => {
            const IconComponent = iconMap[agent.icon] || BotIcon;
            const isEnabled = enabledAgents[agent.id] !== false;

            return (
              <Tooltip key={agent.id} delayDuration={300}>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-2 py-2.5",
                      "cursor-pointer select-none transition-colors",
                      "hover:bg-muted/50",
                      !isEnabled && "opacity-50",
                    )}
                    onClick={() => handleToggle(agent.id, !isEnabled)}
                  >
                    <IconComponent
                      className={cn(
                        "size-4 shrink-0 transition-colors",
                        isEnabled ? "text-foreground/70" : "text-muted-foreground/40",
                      )}
                    />
                    <span className="flex-1 text-sm font-medium">{agent.name}</span>
                    <Switch
                      checked={isEnabled}
                      onCheckedChange={(checked) => handleToggle(agent.id, checked)}
                      onClick={(e) => e.stopPropagation()}
                      className="shrink-0 scale-90"
                    />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right" align="center" className="max-w-[200px] bg-popover text-popover-foreground shadow-xl border-border/40">
                  <p className="text-[11px] leading-tight text-muted-foreground/90">{agent.description}</p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>

        <div className="border-t border-border/30 px-3 py-2 text-[11px] text-muted-foreground/50">
          Changes apply to the next message.
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
