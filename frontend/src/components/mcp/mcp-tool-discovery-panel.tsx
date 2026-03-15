"use client";

import { useTranslations } from "next-intl";
import type { McpDiscoverResponse } from "@/types/models";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { McpToolCard } from "@/components/mcp/mcp-tool-card";
import { RefreshCw, Save, Plug, AlertCircle, Loader2 } from "lucide-react";

interface McpToolDiscoveryPanelProps {
  results: McpDiscoverResponse[];
  discovering: boolean;
  syncing: boolean;
  showSyncButton: boolean;
  onDiscover?: () => void;
  onSync?: () => void;
}

export function McpToolDiscoveryPanel({
  results,
  discovering,
  syncing,
  showSyncButton,
  onDiscover,
  onSync,
}: McpToolDiscoveryPanelProps) {
  const ts = useTranslations("system");

  const totalTools = results.reduce((sum, r) => sum + r.tools.length, 0);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Plug className="h-4 w-4" />
              {ts("discoveredTools")}
              {totalTools > 0 && (
                <Badge variant="secondary" className="text-[10px]">
                  {totalTools}
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              {ts("discoveredToolsDesc")}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {onDiscover && (
              <Button
                size="sm"
                variant="outline"
                onClick={onDiscover}
                disabled={discovering || syncing}
                className="gap-1.5"
              >
                {discovering ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                {discovering ? ts("discovering") : ts("discoverTools")}
              </Button>
            )}
            {showSyncButton && totalTools > 0 && (
              <Button
                size="sm"
                onClick={onSync}
                disabled={syncing || discovering}
                className="gap-1.5"
              >
                {syncing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                {syncing ? ts("syncing") : ts("syncTools")}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="max-h-[50vh] overflow-y-auto">
        {results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Plug className="h-10 w-10 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">
              {ts("noToolsDiscovered")}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {results.map((result) => (
              <McpServerToolGroup key={result.server_name} result={result} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Renders tools grouped by MCP server name */
function McpServerToolGroup({ result }: { result: McpDiscoverResponse }) {
  if (result.error) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-destructive">
          <AlertCircle className="h-4 w-4" />
          {result.server_name}
        </div>
        <p className="text-xs text-destructive/80 mt-1">{result.error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-sm font-semibold">{result.server_name}</h3>
        <Badge variant="outline" className="text-[10px]">
          {result.tools.length} tools
        </Badge>
      </div>
      <div className="grid gap-2">
        {result.tools.map((tool) => (
          <McpToolCard key={tool.name} tool={tool} />
        ))}
      </div>
    </div>
  );
}
