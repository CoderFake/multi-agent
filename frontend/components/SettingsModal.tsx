'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { X, Server, Database } from 'lucide-react';
import { McpManager } from '@/components/settings/McpManager';
import { KnowledgeManager } from '@/components/settings/KnowledgeManager';
import { cn } from '@/lib/utils';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type Tab = 'mcp' | 'knowledge';

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [tab, setTab] = useState<Tab>('mcp');

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-background rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b">
                    <h2 className="text-xl font-semibold">Settings</h2>
                    <Button variant="ghost" size="icon" onClick={onClose}>
                        <X className="h-5 w-5" />
                    </Button>
                </div>

                {/* Tabs */}
                <div className="flex border-b px-6">
                    <button
                        onClick={() => setTab('mcp')}
                        className={cn(
                            "flex items-center gap-2 px-1 py-3 text-sm font-medium border-b-2 transition-colors mr-6",
                            tab === 'mcp'
                                ? "border-[#6766FC] text-[#6766FC]"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        )}
                    >
                        <Server className="h-4 w-4" />
                        MCP Servers
                    </button>
                    <button
                        onClick={() => setTab('knowledge')}
                        className={cn(
                            "flex items-center gap-2 px-1 py-3 text-sm font-medium border-b-2 transition-colors",
                            tab === 'knowledge'
                                ? "border-[#6766FC] text-[#6766FC]"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        )}
                    >
                        <Database className="h-4 w-4" />
                        Knowledge Base
                    </button>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {tab === 'mcp' && <McpManager />}
                    {tab === 'knowledge' && <KnowledgeManager />}
                </div>
            </div>
        </div>
    );
}
