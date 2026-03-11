"use client";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";
import { Streamdown } from "streamdown";
import type { ToolRendererProps } from "./types";
import { cleanResultText, extractResultText } from "../utils";
import { extractQueryAttemptsData, QueryAttemptsDisplay } from "../query-attempts-display";

/**
 * Data analyst renderer showing technical query details.
 * Shows:
 * - Query history (all attempts with status, expandable SQL)
 * - Synopsis text from the agent
 *
 * Note: Chart widgets are extracted at ToolCallDisplay level and rendered
 * outside the collapsible for visibility. This renderer receives the cleaned
 * result with widget tags already removed.
 */
export function DataAnalystRenderer({ output, error }: ToolRendererProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (error) {
    return (
      <div className="mt-2 border-t border-border/30 pt-2">
        <span className="text-[10px] tracking-wide text-muted-foreground/70 uppercase">Error</span>
        <div className="mt-1 text-destructive">{error}</div>
      </div>
    );
  }

  if (!output) {
    return null;
  }

  const resultText = extractResultText(output);

  if (!resultText) {
    return null;
  }

  // Extract query attempts (widgets already extracted at ToolCallDisplay level)
  const { data: queryData, cleanedText: textWithoutQueries } = extractQueryAttemptsData(resultText);

  // Final cleaned text for synopsis
  const cleanedText = cleanResultText(textWithoutQueries);

  const isLong = cleanedText.length > 300;
  const previewText = isLong ? cleanedText.slice(0, 300) + "..." : cleanedText;

  return (
    <div className="mt-2 space-y-3 border-t border-border/30 pt-2">
      {/* Query attempts - technical details for debugging */}
      {queryData && <QueryAttemptsDisplay data={queryData} />}

      {/* Synopsis */}
      {cleanedText && (
        <div>
          <span className="text-[10px] tracking-wide text-muted-foreground/70 uppercase">
            Synopsis
          </span>
          <div className="mt-1 text-xs text-muted-foreground">
            {isLong ? (
              <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
                <CollapsibleContent>
                  <Streamdown className="prose prose-sm prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                    {cleanedText}
                  </Streamdown>
                </CollapsibleContent>
                {!isExpanded && (
                  <Streamdown className="prose prose-sm prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                    {previewText}
                  </Streamdown>
                )}
                <CollapsibleTrigger className="mt-2 text-[10px] text-primary hover:underline">
                  {isExpanded ? "Show less" : "Show more"}
                </CollapsibleTrigger>
              </Collapsible>
            ) : (
              <Streamdown className="prose prose-sm prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                {cleanedText}
              </Streamdown>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
