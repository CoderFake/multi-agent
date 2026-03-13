"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, Check, Search, X } from "lucide-react";

export interface ComboboxOption {
    value: string;
    label: string;
    description?: string;
}

interface ComboboxProps {
    options: ComboboxOption[];
    value: string;
    onValueChange: (value: string) => void;
    placeholder?: string;
    searchPlaceholder?: string;
    emptyText?: string;
    className?: string;
    disabled?: boolean;
}

export function Combobox({
    options,
    value,
    onValueChange,
    placeholder = "Select...",
    searchPlaceholder = "Search...",
    emptyText = "No results found",
    className,
    disabled = false,
}: ComboboxProps) {
    const [open, setOpen] = React.useState(false);
    const [search, setSearch] = React.useState("");
    const containerRef = React.useRef<HTMLDivElement>(null);
    const inputRef = React.useRef<HTMLInputElement>(null);

    // Close on outside click
    React.useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    // Close on escape
    React.useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === "Escape") setOpen(false);
        };
        if (open) document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, [open]);

    const filtered = React.useMemo(() => {
        if (!search.trim()) return options;
        const q = search.toLowerCase();
        return options.filter(
            (o) =>
                o.label.toLowerCase().includes(q) ||
                o.value.toLowerCase().includes(q) ||
                o.description?.toLowerCase().includes(q),
        );
    }, [options, search]);

    const selectedOption = options.find((o) => o.value === value);

    const handleSelect = (val: string) => {
        onValueChange(val);
        setOpen(false);
        setSearch("");
    };

    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation();
        onValueChange("");
        setSearch("");
    };

    return (
        <div ref={containerRef} className={cn("relative", className)}>
            {/* Trigger */}
            <button
                type="button"
                disabled={disabled}
                onClick={() => {
                    setOpen(!open);
                    if (!open) setTimeout(() => inputRef.current?.focus(), 50);
                }}
                className={cn(
                    "flex w-full items-center justify-between rounded-md border border-border/60 bg-transparent px-3 py-2 text-sm",
                    "hover:bg-accent/50 transition-colors",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                    open && "ring-1 ring-ring/30",
                )}
            >
                <span className={cn("truncate", !selectedOption && "text-muted-foreground")}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <div className="flex items-center gap-1 ml-2 shrink-0">
                    {value && (
                        <span
                            role="button"
                            tabIndex={-1}
                            onClick={handleClear}
                            className="rounded-sm p-0.5 hover:bg-muted"
                        >
                            <X className="h-3 w-3 text-muted-foreground" />
                        </span>
                    )}
                    <ChevronDown
                        className={cn(
                            "h-4 w-4 text-muted-foreground transition-transform",
                            open && "rotate-180",
                        )}
                    />
                </div>
            </button>

            {/* Dropdown */}
            {open && (
                <div className="absolute z-50 mt-1 w-full rounded-md border border-border/60 bg-popover shadow-md animate-in fade-in-0 zoom-in-95">
                    {/* Search input */}
                    <div className="flex items-center gap-2 border-b border-border/40 px-3 py-2">
                        <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                        <input
                            ref={inputRef}
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder={searchPlaceholder}
                            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                        />
                    </div>

                    {/* Options list */}
                    <div className="max-h-[200px] overflow-y-auto p-1">
                        {filtered.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-4">
                                {emptyText}
                            </p>
                        ) : (
                            filtered.map((option) => (
                                <button
                                    key={option.value}
                                    type="button"
                                    onClick={() => handleSelect(option.value)}
                                    className={cn(
                                        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm cursor-pointer",
                                        "hover:bg-accent hover:text-accent-foreground",
                                        value === option.value && "bg-accent/50",
                                    )}
                                >
                                    <Check
                                        className={cn(
                                            "h-4 w-4 shrink-0",
                                            value === option.value ? "opacity-100" : "opacity-0",
                                        )}
                                    />
                                    <div className="flex-1 text-left truncate">
                                        <span>{option.label}</span>
                                        {option.description && (
                                            <span className="ml-2 text-xs text-muted-foreground">
                                                {option.description}
                                            </span>
                                        )}
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
