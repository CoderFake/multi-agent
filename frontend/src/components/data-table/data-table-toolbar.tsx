"use client";

import { type ReactNode } from "react";
import { SearchInput } from "@/components/shared/search-input";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DataTableToolbarProps {
  /** Search callback — debounced by SearchInput */
  onSearch?: (value: string) => void;
  /** Search placeholder */
  searchPlaceholder?: string;
  /** Whether filters are active (shows reset button) */
  isFiltered?: boolean;
  /** Reset all filters callback */
  onReset?: () => void;
  /** Filter components (dropdowns, selects, etc.) */
  filters?: ReactNode;
  /** Action buttons (create, export, etc.) — rendered on the right */
  actions?: ReactNode;
  className?: string;
}

export function DataTableToolbar({
  onSearch,
  searchPlaceholder = "Search...",
  isFiltered = false,
  onReset,
  filters,
  actions,
  className,
}: DataTableToolbarProps) {
  return (
    <div className={cn("flex items-center justify-between gap-2", className)}>
      <div className="flex flex-1 items-center gap-2">
        {onSearch && (
          <SearchInput
            placeholder={searchPlaceholder}
            onSearch={onSearch}
            className="w-64"
          />
        )}
        {filters}
        {isFiltered && onReset && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="h-8 px-2 text-muted-foreground"
          >
            Reset
            <X className="ml-1 h-3.5 w-3.5" />
          </Button>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}
