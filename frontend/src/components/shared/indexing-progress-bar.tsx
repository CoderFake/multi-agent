/**
 * IndexingProgressBar — common component showing document indexing progress.
 * Animated bar with status text. Used inline in document rows.
 */
"use client";

import { cn } from "@/lib/utils";

export interface IndexingProgressBarProps {
  /** 0-100 percentage */
  progress: number;
  /** Current status label */
  status: string;
  /** Optional status message */
  message?: string;
  /** Size variant */
  size?: "sm" | "md";
  className?: string;
}

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-muted-foreground/40",
  extracting: "bg-blue-500",
  chunking: "bg-indigo-500",
  embedding: "bg-violet-500",
  indexing: "bg-amber-500",
  completed: "bg-emerald-500",
  failed: "bg-destructive",
};

export function IndexingProgressBar({
  progress,
  status,
  message,
  size = "sm",
  className,
}: IndexingProgressBarProps) {
  const barColor = STATUS_COLORS[status] || "bg-primary";
  const height = size === "sm" ? "h-1.5" : "h-2.5";
  const isActive = !["completed", "failed"].includes(status);

  return (
    <div className={cn("w-full space-y-1", className)}>
      {/* Track */}
      <div className={cn("w-full rounded-full bg-muted overflow-hidden", height)}>
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500 ease-out",
            barColor,
            isActive && "animate-pulse",
          )}
          style={{ width: `${Math.max(progress, 2)}%` }}
        />
      </div>
      {/* Status text */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-muted-foreground truncate">
          {message || status}
        </span>
        <span className="text-[10px] text-muted-foreground font-mono shrink-0">
          {progress}%
        </span>
      </div>
    </div>
  );
}
