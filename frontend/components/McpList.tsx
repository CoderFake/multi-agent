'use client';

import { useState, useEffect } from 'react';
import { Trash2, Wrench, Server, ChevronDown, ChevronUp } from 'lucide-react';
import { api, MCPConfig } from '@/lib/api';
import { cn } from '@/lib/utils';

interface McpListProps {
    mcps: MCPConfig[];
    onMCPDeleted: (id: string) => void;
}

export default function McpList({ mcps, onMCPDeleted }: McpListProps) {
    const [expandedMCP, setExpandedMCP] = useState<string | null>(null);
    const [mcpTools, setMcpTools] = useState<Record<string, any>>({});

    const loadTools = async (mcpId: string) => {
        if (mcpTools[mcpId]) {
            setExpandedMCP(expandedMCP === mcpId ? null : mcpId);
            return;
        }

        try {
            const data = await api.getMCPTools(mcpId);
            setMcpTools({ ...mcpTools, [mcpId]: data.tools });
            setExpandedMCP(mcpId);
        } catch (err) {
            console.error('Failed to load tools:', err);
        }
    };

    const handleDelete = async (mcpId: string) => {
        if (!confirm('Are you sure you want to unload this MCP?')) return;

        try {
            await api.deleteMCP(mcpId);
            onMCPDeleted(mcpId);
        } catch (err) {
            console.error('Failed to delete MCP:', err);
        }
    };

    return (
        <div className="space-y-4">
            <div>
                <h2 className="text-2xl font-bold mb-2">Loaded MCPs</h2>
                <p className="text-muted-foreground">
                    {mcps.length} MCP server{mcps.length !== 1 ? 's' : ''} loaded
                </p>
            </div>

            {mcps.length === 0 ? (
                <div className="p-8 border-2 border-dashed rounded-lg text-center text-muted-foreground">
                    <Server className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No MCPs loaded yet</p>
                    <p className="text-sm">Import an MCP configuration to get started</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {mcps.map((mcp) => (
                        <div
                            key={mcp.id}
                            className="border rounded-lg p-4 hover:border-primary/50 transition-colors"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <Server className="w-5 h-5 text-primary" />
                                        <h3 className="font-semibold">{mcp.name}</h3>
                                        <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full">
                                            {mcp.protocol.toUpperCase()}
                                        </span>
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        {mcp.tools_count} tool{mcp.tools_count !== 1 ? 's' : ''} available
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => loadTools(mcp.id)}
                                        className="p-2 hover:bg-secondary rounded-lg transition-colors"
                                        title="View tools"
                                    >
                                        {expandedMCP === mcp.id ? (
                                            <ChevronUp className="w-4 h-4" />
                                        ) : (
                                            <ChevronDown className="w-4 h-4" />
                                        )}
                                    </button>
                                    <button
                                        onClick={() => handleDelete(mcp.id)}
                                        className="p-2 hover:bg-destructive/10 text-destructive rounded-lg transition-colors"
                                        title="Unload MCP"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            {/* Tools List */}
                            {expandedMCP === mcp.id && mcpTools[mcp.id] && (
                                <div className="mt-4 pt-4 border-t space-y-2">
                                    <div className="flex items-center gap-2 text-sm font-medium mb-3">
                                        <Wrench className="w-4 h-4" />
                                        Available Tools
                                    </div>
                                    {mcpTools[mcp.id].length === 0 ? (
                                        <p className="text-sm text-muted-foreground">No tools defined</p>
                                    ) : (
                                        <div className="space-y-2">
                                            {mcpTools[mcp.id].map((tool: any, idx: number) => (
                                                <div
                                                    key={idx}
                                                    className="p-3 bg-secondary/50 rounded-lg"
                                                >
                                                    <div className="font-mono text-sm font-semibold mb-1">
                                                        {tool.name || 'Unnamed Tool'}
                                                    </div>
                                                    {tool.description && (
                                                        <p className="text-xs text-muted-foreground">
                                                            {tool.description}
                                                        </p>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
