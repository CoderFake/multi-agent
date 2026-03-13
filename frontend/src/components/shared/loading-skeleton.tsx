"use client";

import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  /** Number of skeleton rows */
  rows?: number;
  /** Number of skeleton columns */
  columns?: number;
  /** Show page-level skeleton (title + description + table) */
  variant?: "table" | "page" | "card";
  className?: string;
}

function SkeletonLine({ className }: { className?: string }) {
  return (
    <div
      className={cn("h-4 animate-pulse rounded bg-muted", className)}
    />
  );
}

function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="rounded-lg border border-border/50 bg-card">
      {/* Header */}
      <div className="border-b border-border/50 bg-muted/30 px-4 py-3 flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <SkeletonLine key={i} className="h-4 w-24" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="border-b border-border/40 px-4 py-3 flex gap-4 last:border-b-0">
          {Array.from({ length: columns }).map((_, j) => (
            <SkeletonLine
              key={j}
              className={cn("h-4", j === 0 ? "w-32" : "w-20")}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="space-y-2">
        <SkeletonLine className="h-8 w-48" />
        <SkeletonLine className="h-4 w-72" />
      </div>
      {/* Toolbar */}
      <div className="flex items-center gap-2">
        <SkeletonLine className="h-9 w-64" />
        <SkeletonLine className="h-9 w-24 ml-auto" />
      </div>
      {/* Table */}
      <TableSkeleton rows={5} columns={4} />
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="rounded-lg border border-border/50 bg-card p-6 space-y-4">
      <SkeletonLine className="h-5 w-32" />
      <SkeletonLine className="h-4 w-full" />
      <SkeletonLine className="h-4 w-3/4" />
      <SkeletonLine className="h-4 w-1/2" />
    </div>
  );
}

export function LoadingSkeleton({
  rows = 5,
  columns = 4,
  variant = "table",
  className,
}: LoadingSkeletonProps) {
  return (
    <div className={cn("w-full", className)}>
      {variant === "page" && <PageSkeleton />}
      {variant === "table" && <TableSkeleton rows={rows} columns={columns} />}
      {variant === "card" && <CardSkeleton />}
    </div>
  );
}
