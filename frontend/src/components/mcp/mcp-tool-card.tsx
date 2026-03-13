"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import type { DiscoveredTool } from "@/types/models";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Wrench, ChevronDown, ChevronRight } from "lucide-react";

interface McpToolCardProps {
  tool: DiscoveredTool;
}

export function McpToolCard({ tool }: McpToolCardProps) {
  const ts = useTranslations("system");
  const [open, setOpen] = useState(false);

  const inputSchema = tool.input_schema as Record<string, unknown> | null;
  const properties = (inputSchema?.properties ?? {}) as Record<string, Record<string, unknown>>;
  const required = (inputSchema?.required ?? []) as string[];
  const paramKeys = Object.keys(properties);

  return (
    <Card className="transition-all hover:shadow-md border-border/60">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Wrench className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold truncate">{tool.name}</h4>
              {paramKeys.length > 0 && (
                <Badge variant="secondary" className="text-[10px] shrink-0">
                  {paramKeys.length} {ts("parameters").toLowerCase()}
                </Badge>
              )}
            </div>
            {tool.description && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {tool.description}
              </p>
            )}

            {paramKeys.length > 0 && (
              <Collapsible open={open} onOpenChange={setOpen} className="mt-2">
                <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                  {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  {ts("parameters")}
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="rounded-md bg-muted/50 p-2 space-y-1">
                    {paramKeys.map((key) => {
                      const prop = properties[key];
                      const isRequired = required.includes(key);
                      const propType = prop?.type != null ? String(prop.type) : null;
                      const propDesc = prop?.description != null ? String(prop.description) : null;
                      return (
                        <div key={key} className="text-xs">
                          <div className="flex items-baseline gap-2 flex-wrap">
                            <code className="font-mono text-primary/80">{key}</code>
                            {propType && (
                              <span className="text-muted-foreground">
                                ({propType})
                              </span>
                            )}
                            {isRequired && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0">
                                required
                              </Badge>
                            )}
                          </div>
                          {propDesc && (
                            <p className="text-muted-foreground mt-0.5 break-words">
                              {propDesc}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
