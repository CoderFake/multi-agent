'use client';

import { Button } from '@/components/ui/button';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import { Trash2, Undo2, Github, Settings } from 'lucide-react';

interface NavBarProps {
    onClear?: () => void;
    onUndo?: () => void;
    onSettings?: () => void;
    canClear?: boolean;
    canUndo?: boolean;
}

export function NavBar({
    onClear,
    onUndo,
    onSettings,
    canClear = false,
    canUndo = false,
}: NavBarProps) {
    return (
        <div className="border-b bg-background">
            <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <h1 className="text-lg font-semibold">FastMCP</h1>
                    <span className="text-xs text-muted-foreground px-2 py-1 bg-muted rounded">
                        AI Assistant
                    </span>
                </div>

                <div className="flex items-center gap-1">
                    <TooltipProvider>
                        {canUndo && onUndo && (
                            <Tooltip delayDuration={0}>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={onUndo}
                                        className="h-9 w-9"
                                    >
                                        <Undo2 className="h-4 w-4" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>Undo last message</TooltipContent>
                            </Tooltip>
                        )}

                        {canClear && onClear && (
                            <Tooltip delayDuration={0}>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={onClear}
                                        className="h-9 w-9"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>Clear chat</TooltipContent>
                            </Tooltip>
                        )}

                        {onSettings && (
                            <Tooltip delayDuration={0}>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={onSettings}
                                        className="h-9 w-9"
                                    >
                                        <Settings className="h-4 w-4" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>Settings</TooltipContent>
                            </Tooltip>
                        )}

                        <Tooltip delayDuration={0}>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    asChild
                                    className="h-9 w-9"
                                >
                                    <a
                                        href="https://github.com/e2b-dev/fragments"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        <Github className="h-4 w-4" />
                                    </a>
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>View on GitHub</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>
            </div>
        </div>
    );
}
