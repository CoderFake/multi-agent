'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import McpImporter from '@/components/McpImporter';
import McpList from '@/components/McpList';
import { api, MCPConfig } from '@/lib/api';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [mcps, setMcps] = useState<MCPConfig[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen) {
            loadMCPs();
        }
    }, [isOpen]);

    const loadMCPs = async () => {
        try {
            const data = await api.listMCPs();
            setMcps(data);
        } catch (err) {
            console.error('Failed to load MCPs:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleMCPImported = (mcp: MCPConfig) => {
        setMcps([...mcps, mcp]);
    };

    const handleMCPDeleted = (id: string) => {
        setMcps(mcps.filter((m) => m.id !== id));
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-background rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                <div className="flex items-center justify-between p-6 border-b">
                    <div>
                        <h2 className="text-2xl font-bold">MCP Server Settings</h2>
                        <p className="text-sm text-muted-foreground">
                            Manage your Model Context Protocol servers
                        </p>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose}>
                        <X className="h-5 w-5" />
                    </Button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    <McpImporter onMCPImported={handleMCPImported} />
                    <McpList mcps={mcps} onMCPDeleted={handleMCPDeleted} />
                </div>
            </div>
        </div>
    );
}
