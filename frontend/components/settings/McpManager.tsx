'use client';

import { useState, useRef, useEffect } from 'react';
import {
    Upload, FileJson, Loader2, CheckCircle, XCircle,
    Plus, Trash2, Code, Server, Wrench, ChevronDown, ChevronUp,
} from 'lucide-react';
import { api, MCPConfig } from '@/lib/api';
import { cn } from '@/lib/utils';

// ── Types ──────────────────────────────────────────────────────────────

interface Header {
    key: string;
    value: string;
}

// ── McpImporter (inline) ───────────────────────────────────────────────

function McpImporter({ onMCPImported }: { onMCPImported: (mcp: MCPConfig) => void }) {
    const [protocol, setProtocol] = useState<'sse' | 'stdio'>('sse');
    const [inputMode, setInputMode] = useState<'form' | 'json'>('form');

    const [name, setName] = useState('');
    const [url, setUrl] = useState('');
    const [headers, setHeaders] = useState<Header[]>([{ key: '', value: '' }]);
    const [command, setCommand] = useState('');
    const [args, setArgs] = useState('');
    const [jsonInput, setJsonInput] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const addHeader = () => setHeaders([...headers, { key: '', value: '' }]);
    const removeHeader = (i: number) => setHeaders(headers.filter((_, idx) => idx !== i));
    const updateHeader = (i: number, field: 'key' | 'value', val: string) => {
        const h = [...headers];
        h[i][field] = val;
        setHeaders(h);
    };

    const buildConfig = () => {
        if (protocol === 'sse') {
            const config: any = { url: url.trim() };
            const filled = headers.filter(h => h.key.trim() && h.value.trim());
            if (filled.length) config.headers = Object.fromEntries(filled.map(h => [h.key.trim(), h.value.trim()]));
            return config;
        }
        const config: any = { command: command.trim() };
        if (args.trim()) config.args = args.trim().split(/\s+/);
        return config;
    };

    const validate = (): string | null => {
        if (protocol === 'sse') {
            if (!url.trim()) return 'URL is required for SSE protocol';
            try { new URL(url); } catch { return 'Invalid URL format'; }
        } else {
            if (!command.trim()) return 'Command is required for stdio protocol';
        }
        return null;
    };

    const handleFormSubmit = async () => {
        const err = validate();
        if (err) { setError(err); return; }
        setLoading(true); setError(''); setSuccess('');
        try {
            const mcp = await api.importMCP({ name: name.trim() || undefined, protocol, config: buildConfig() });
            setSuccess(`MCP "${mcp.name}" imported successfully!`);
            onMCPImported(mcp);
            setName(''); setUrl(''); setHeaders([{ key: '', value: '' }]); setCommand(''); setArgs('');
        } catch (e: any) {
            setError(e.message || 'Failed to import MCP');
        } finally { setLoading(false); }
    };

    const handleJSONSubmit = async () => {
        setLoading(true); setError(''); setSuccess('');
        try {
            const mcp = await api.importMCP({ protocol, config: JSON.parse(jsonInput) });
            setSuccess(`MCP "${mcp.name}" imported successfully!`);
            onMCPImported(mcp);
            setJsonInput('');
        } catch (e: any) {
            setError(e.message || 'Failed to import MCP');
        } finally { setLoading(false); }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setLoading(true); setError(''); setSuccess('');
        try {
            const mcp = await api.importMCPFromFile(file);
            setSuccess(`MCP "${mcp.name}" imported from file!`);
            onMCPImported(mcp);
        } catch (e: any) {
            setError(e.message || 'Failed to import MCP from file');
        } finally { setLoading(false); }
    };

    const exampleConfig = protocol === 'sse'
        ? `{\n  "name": "My SSE MCP",\n  "url": "https://api.example.com/mcp",\n  "headers": { "Authorization": "Bearer token" }\n}`
        : `{\n  "name": "My stdio MCP",\n  "command": "npx",\n  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]\n}`;

    return (
        <div className="space-y-4">
            <div>
                <h3 className="text-base font-semibold mb-1">Import MCP Server</h3>
                <p className="text-sm text-muted-foreground">Add an MCP server via form or JSON configuration.</p>
            </div>

            {/* Protocol */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium">Protocol</label>
                <div className="flex gap-3">
                    {(['sse', 'stdio'] as const).map(p => (
                        <button key={p} onClick={() => setProtocol(p)}
                            className={cn('px-3 py-1.5 rounded-lg border-2 text-sm transition-colors',
                                protocol === p ? 'border-[#6766FC] bg-[#f0f0ff] text-[#6766FC]' : 'border-border hover:border-[#6766FC]/50'
                            )}>
                            {p === 'sse' ? 'SSE' : 'stdio'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Input Mode */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium">Input Mode</label>
                <div className="flex gap-3">
                    <button onClick={() => setInputMode('form')}
                        className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg border-2 text-sm transition-colors',
                            inputMode === 'form' ? 'border-[#6766FC] bg-[#f0f0ff] text-[#6766FC]' : 'border-border hover:border-[#6766FC]/50'
                        )}>
                        <Upload className="w-3.5 h-3.5" /> Form
                    </button>
                    <button onClick={() => setInputMode('json')}
                        className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg border-2 text-sm transition-colors',
                            inputMode === 'json' ? 'border-[#6766FC] bg-[#f0f0ff] text-[#6766FC]' : 'border-border hover:border-[#6766FC]/50'
                        )}>
                        <Code className="w-3.5 h-3.5" /> JSON
                    </button>
                </div>
            </div>

            {/* Form Mode */}
            {inputMode === 'form' && (
                <div className="space-y-3 p-4 border rounded-xl bg-gray-50/50">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium">Name (optional)</label>
                        <input type="text" value={name} onChange={e => setName(e.target.value)}
                            placeholder="My MCP Server"
                            className="w-full px-3 py-2 rounded-lg border bg-background text-sm" disabled={loading} />
                    </div>

                    {protocol === 'sse' ? (
                        <>
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium">URL <span className="text-destructive">*</span></label>
                                <input type="url" value={url} onChange={e => setUrl(e.target.value)}
                                    placeholder="https://api.example.com/mcp"
                                    className="w-full px-3 py-2 rounded-lg border bg-background text-sm" disabled={loading} />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium">Headers (optional)</label>
                                <div className="space-y-2">
                                    {headers.map((h, i) => (
                                        <div key={i} className="flex gap-2">
                                            <input type="text" value={h.key} onChange={e => updateHeader(i, 'key', e.target.value)}
                                                placeholder="Header name" className="flex-1 px-3 py-2 rounded-lg border bg-background text-sm" disabled={loading} />
                                            <input type="text" value={h.value} onChange={e => updateHeader(i, 'value', e.target.value)}
                                                placeholder="Header value" className="flex-1 px-3 py-2 rounded-lg border bg-background text-sm" disabled={loading} />
                                            {headers.length > 1 && (
                                                <button onClick={() => removeHeader(i)}
                                                    className="px-2 py-2 rounded-lg border border-destructive/30 hover:bg-destructive/10 text-destructive" disabled={loading}>
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                    <button onClick={addHeader} disabled={loading}
                                        className="w-full px-3 py-1.5 rounded-lg border-2 border-dashed text-sm hover:border-[#6766FC]/50 flex items-center justify-center gap-1.5 text-muted-foreground hover:text-foreground">
                                        <Plus className="w-3.5 h-3.5" /> Add Header
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium">Command <span className="text-destructive">*</span></label>
                                <input type="text" value={command} onChange={e => setCommand(e.target.value)}
                                    placeholder="npx" className="w-full px-3 py-2 rounded-lg border bg-background text-sm" disabled={loading} />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium">Arguments (optional)</label>
                                <input type="text" value={args} onChange={e => setArgs(e.target.value)}
                                    placeholder="-y @modelcontextprotocol/server-filesystem /path"
                                    className="w-full px-3 py-2 rounded-lg border bg-background text-sm" disabled={loading} />
                                <p className="text-xs text-muted-foreground">Space-separated arguments</p>
                            </div>
                        </>
                    )}

                    <button onClick={handleFormSubmit} disabled={loading}
                        className="w-full px-4 py-2 bg-[#6766FC] text-white rounded-lg hover:bg-[#5554e0] disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-medium">
                        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Importing…</> : <><Upload className="w-4 h-4" /> Import MCP Server</>}
                    </button>
                </div>
            )}

            {/* JSON Mode */}
            {inputMode === 'json' && (
                <div className="space-y-3">
                    <textarea value={jsonInput} onChange={e => setJsonInput(e.target.value)}
                        placeholder={exampleConfig}
                        className="w-full h-40 p-3 rounded-xl border bg-background font-mono text-sm resize-none" disabled={loading} />
                    <button onClick={handleJSONSubmit} disabled={loading || !jsonInput.trim()}
                        className="w-full px-4 py-2 bg-[#6766FC] text-white rounded-lg hover:bg-[#5554e0] disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-medium">
                        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Importing…</> : <><FileJson className="w-4 h-4" /> Import from JSON</>}
                    </button>
                    <label className="w-full px-4 py-2.5 border-2 border-dashed rounded-xl hover:border-[#6766FC]/50 transition-colors cursor-pointer flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                        <Upload className="w-4 h-4" /> Upload JSON file
                        <input type="file" accept=".json" onChange={handleFileUpload} className="hidden" disabled={loading} />
                    </label>
                </div>
            )}

            {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-destructive text-sm">
                    <XCircle className="w-4 h-4 flex-shrink-0" /> {error}
                </div>
            )}
            {success && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-2 text-green-600 text-sm">
                    <CheckCircle className="w-4 h-4 flex-shrink-0" /> {success}
                </div>
            )}
        </div>
    );
}

// ── McpList (inline) ───────────────────────────────────────────────────

function McpList({ mcps, onMCPDeleted }: { mcps: MCPConfig[]; onMCPDeleted: (id: string) => void }) {
    const [expanded, setExpanded] = useState<string | null>(null);
    const [tools, setTools] = useState<Record<string, any>>({});

    const loadTools = async (id: string) => {
        if (tools[id]) { setExpanded(expanded === id ? null : id); return; }
        try {
            const data = await api.getMCPTools(id);
            setTools({ ...tools, [id]: data.tools });
            setExpanded(id);
        } catch (e) { console.error('Failed to load tools:', e); }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Unload this MCP server?')) return;
        try { await api.deleteMCP(id); onMCPDeleted(id); }
        catch (e) { console.error('Failed to delete MCP:', e); }
    };

    if (mcps.length === 0) return (
        <div className="py-8 border-2 border-dashed rounded-xl text-center text-muted-foreground">
            <Server className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No MCP servers loaded yet</p>
        </div>
    );

    return (
        <div className="space-y-2">
            {mcps.map(mcp => (
                <div key={mcp.id} className="border rounded-xl p-3 hover:border-[#6766FC]/30 transition-colors">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                            <Server className="w-4 h-4 text-[#6766FC] flex-shrink-0" />
                            <span className="font-medium text-sm truncate">{mcp.name}</span>
                            <span className="px-1.5 py-0.5 bg-[#f0f0ff] text-[#6766FC] text-xs rounded-full flex-shrink-0">
                                {mcp.protocol.toUpperCase()}
                            </span>
                            <span className="text-xs text-muted-foreground flex-shrink-0">
                                {mcp.tools_count} tool{mcp.tools_count !== 1 ? 's' : ''}
                            </span>
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                            <button onClick={() => loadTools(mcp.id)}
                                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors" title="View tools">
                                {expanded === mcp.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>
                            <button onClick={() => handleDelete(mcp.id)}
                                className="p-1.5 hover:bg-red-50 text-gray-400 hover:text-red-500 rounded-lg transition-colors" title="Unload">
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {expanded === mcp.id && tools[mcp.id] && (
                        <div className="mt-3 pt-3 border-t space-y-1.5">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
                                <Wrench className="w-3.5 h-3.5" /> Tools
                            </div>
                            {tools[mcp.id].length === 0 ? (
                                <p className="text-xs text-muted-foreground">No tools defined</p>
                            ) : (
                                tools[mcp.id].map((tool: any, i: number) => (
                                    <div key={i} className="px-3 py-2 bg-gray-50 rounded-lg">
                                        <p className="font-mono text-xs font-semibold">{tool.name || 'Unnamed Tool'}</p>
                                        {tool.description && <p className="text-xs text-muted-foreground mt-0.5">{tool.description}</p>}
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

// ── McpManager (exported) ──────────────────────────────────────────────

export function McpManager() {
    const [mcps, setMcps] = useState<MCPConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const loadedRef = useRef(false);

    useEffect(() => {
        if (loadedRef.current) return;
        loadedRef.current = true;
        api.listMCPs()
            .then(setMcps)
            .catch(e => console.error('Failed to load MCPs:', e))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-base font-semibold mb-1">MCP Servers</h3>
                <p className="text-sm text-muted-foreground">
                    Connect external tools to the agent via Model Context Protocol.
                </p>
            </div>

            <McpImporter onMCPImported={mcp => setMcps(prev => [...prev, mcp])} />

            <div>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-muted-foreground">
                        {loading ? 'Loading…' : `${mcps.length} server${mcps.length !== 1 ? 's' : ''} loaded`}
                    </span>
                </div>
                {loading ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <McpList mcps={mcps} onMCPDeleted={id => setMcps(prev => prev.filter(m => m.id !== id))} />
                )}
            </div>
        </div>
    );
}
