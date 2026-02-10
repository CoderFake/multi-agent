'use client';

import { useState } from 'react';
import { Upload, FileJson, Loader2, CheckCircle, XCircle, Plus, Trash2, Code } from 'lucide-react';
import { api, MCPConfig } from '@/lib/api';
import { cn } from '@/lib/utils';

interface McpImporterProps {
    onMCPImported: (mcp: MCPConfig) => void;
}

interface Header {
    key: string;
    value: string;
}

export default function McpImporter({ onMCPImported }: McpImporterProps) {
    const [protocol, setProtocol] = useState<'sse' | 'stdio'>('sse');
    const [inputMode, setInputMode] = useState<'form' | 'json'>('form');

    // Form fields
    const [name, setName] = useState('');
    const [url, setUrl] = useState('');
    const [headers, setHeaders] = useState<Header[]>([{ key: '', value: '' }]);

    // stdio fields
    const [command, setCommand] = useState('');
    const [args, setArgs] = useState('');

    // JSON mode
    const [jsonInput, setJsonInput] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const addHeader = () => {
        setHeaders([...headers, { key: '', value: '' }]);
    };

    const removeHeader = (index: number) => {
        setHeaders(headers.filter((_, i) => i !== index));
    };

    const updateHeader = (index: number, field: 'key' | 'value', value: string) => {
        const newHeaders = [...headers];
        newHeaders[index][field] = value;
        setHeaders(newHeaders);
    };

    const buildConfigFromForm = () => {
        if (protocol === 'sse') {
            const config: any = {
                url: url.trim(),
            };

            // Add headers if any are filled
            const filledHeaders = headers.filter(h => h.key.trim() && h.value.trim());
            if (filledHeaders.length > 0) {
                config.headers = Object.fromEntries(
                    filledHeaders.map(h => [h.key.trim(), h.value.trim()])
                );
            }

            return config;
        } else {
            // stdio
            const config: any = {
                command: command.trim(),
            };

            if (args.trim()) {
                config.args = args.trim().split(/\s+/);
            }

            return config;
        }
    };

    const validateForm = (): string | null => {
        if (protocol === 'sse') {
            if (!url.trim()) {
                return 'URL is required for SSE protocol';
            }
            try {
                new URL(url);
            } catch {
                return 'Invalid URL format';
            }
        } else {
            if (!command.trim()) {
                return 'Command is required for stdio protocol';
            }
        }
        return null;
    };

    const handleFormSubmit = async () => {
        const validationError = validateForm();
        if (validationError) {
            setError(validationError);
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const config = buildConfigFromForm();
            const mcp = await api.importMCP({
                name: name.trim() || undefined,
                protocol,
                config,
            });
            setSuccess(`MCP "${mcp.name}" imported successfully!`);
            onMCPImported(mcp);

            // Reset form
            setName('');
            setUrl('');
            setHeaders([{ key: '', value: '' }]);
            setCommand('');
            setArgs('');
        } catch (err: any) {
            setError(err.message || 'Failed to import MCP');
        } finally {
            setLoading(false);
        }
    };

    const handleJSONSubmit = async () => {
        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const config = JSON.parse(jsonInput);
            const mcp = await api.importMCP({
                protocol,
                config,
            });
            setSuccess(`MCP "${mcp.name}" imported successfully!`);
            onMCPImported(mcp);
            setJsonInput('');
        } catch (err: any) {
            setError(err.message || 'Failed to import MCP');
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const mcp = await api.importMCPFromFile(file);
            setSuccess(`MCP "${mcp.name}" imported from file!`);
            onMCPImported(mcp);
        } catch (err: any) {
            setError(err.message || 'Failed to import MCP from file');
        } finally {
            setLoading(false);
        }
    };

    const getExampleConfig = () => {
        if (protocol === 'sse') {
            return `{
  "name": "My SSE MCP Server",
  "url": "https://api.example.com/mcp",
  "headers": {
    "Authorization": "Bearer your-token"
  }
}`;
        } else {
            return `{
  "name": "My stdio MCP Server",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
  "env": {
    "NODE_ENV": "production"
  }
}`;
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold mb-2">Import MCP Configuration</h2>
                <p className="text-muted-foreground">
                    Import MCP servers via form or JSON configuration
                </p>
            </div>

            {/* Protocol Selection */}
            <div className="space-y-2">
                <label className="text-sm font-medium">Protocol Type</label>
                <div className="flex gap-4">
                    <button
                        onClick={() => setProtocol('sse')}
                        className={cn(
                            "px-4 py-2 rounded-lg border-2 transition-colors",
                            protocol === 'sse'
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border hover:border-primary/50"
                        )}
                    >
                        SSE (Server-Sent Events)
                    </button>
                    <button
                        onClick={() => setProtocol('stdio')}
                        className={cn(
                            "px-4 py-2 rounded-lg border-2 transition-colors",
                            protocol === 'stdio'
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border hover:border-primary/50"
                        )}
                    >
                        stdio (Standard I/O)
                    </button>
                </div>
            </div>

            {/* Input Mode Toggle */}
            <div className="space-y-2">
                <label className="text-sm font-medium">Input Mode</label>
                <div className="flex gap-4">
                    <button
                        onClick={() => setInputMode('form')}
                        className={cn(
                            "px-4 py-2 rounded-lg border-2 transition-colors flex items-center gap-2",
                            inputMode === 'form'
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border hover:border-primary/50"
                        )}
                    >
                        <Upload className="w-4 h-4" />
                        Form
                    </button>
                    <button
                        onClick={() => setInputMode('json')}
                        className={cn(
                            "px-4 py-2 rounded-lg border-2 transition-colors flex items-center gap-2",
                            inputMode === 'json'
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border hover:border-primary/50"
                        )}
                    >
                        <Code className="w-4 h-4" />
                        JSON
                    </button>
                </div>
            </div>

            {/* Form Mode */}
            {inputMode === 'form' && (
                <div className="space-y-4 p-4 border rounded-lg bg-card">
                    {/* Name field (common) */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Name (optional)</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="My MCP Server"
                            className="w-full px-3 py-2 rounded-lg border bg-background"
                            disabled={loading}
                        />
                    </div>

                    {protocol === 'sse' ? (
                        <>
                            {/* SSE URL */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    URL <span className="text-destructive">*</span>
                                </label>
                                <input
                                    type="url"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    placeholder="https://api.example.com/mcp"
                                    className="w-full px-3 py-2 rounded-lg border bg-background"
                                    disabled={loading}
                                />
                            </div>

                            {/* SSE Headers */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Headers (optional)</label>
                                <div className="space-y-2">
                                    {headers.map((header, index) => (
                                        <div key={index} className="flex gap-2">
                                            <input
                                                type="text"
                                                value={header.key}
                                                onChange={(e) => updateHeader(index, 'key', e.target.value)}
                                                placeholder="Header name"
                                                className="flex-1 px-3 py-2 rounded-lg border bg-background"
                                                disabled={loading}
                                            />
                                            <input
                                                type="text"
                                                value={header.value}
                                                onChange={(e) => updateHeader(index, 'value', e.target.value)}
                                                placeholder="Header value"
                                                className="flex-1 px-3 py-2 rounded-lg border bg-background"
                                                disabled={loading}
                                            />
                                            {headers.length > 1 && (
                                                <button
                                                    onClick={() => removeHeader(index)}
                                                    className="px-3 py-2 rounded-lg border border-destructive/50 hover:bg-destructive/10 text-destructive"
                                                    disabled={loading}
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                    <button
                                        onClick={addHeader}
                                        className="w-full px-3 py-2 rounded-lg border-2 border-dashed hover:border-primary/50 flex items-center justify-center gap-2 text-muted-foreground hover:text-foreground"
                                        disabled={loading}
                                    >
                                        <Plus className="w-4 h-4" />
                                        Add Header
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            {/* stdio Command */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    Command <span className="text-destructive">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={command}
                                    onChange={(e) => setCommand(e.target.value)}
                                    placeholder="npx"
                                    className="w-full px-3 py-2 rounded-lg border bg-background"
                                    disabled={loading}
                                />
                            </div>

                            {/* stdio Args */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Arguments (optional)</label>
                                <input
                                    type="text"
                                    value={args}
                                    onChange={(e) => setArgs(e.target.value)}
                                    placeholder="-y @modelcontextprotocol/server-filesystem /path"
                                    className="w-full px-3 py-2 rounded-lg border bg-background"
                                    disabled={loading}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Space-separated arguments
                                </p>
                            </div>
                        </>
                    )}

                    <button
                        onClick={handleFormSubmit}
                        disabled={loading}
                        className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Importing...
                            </>
                        ) : (
                            <>
                                <Upload className="w-4 h-4" />
                                Import MCP Server
                            </>
                        )}
                    </button>
                </div>
            )}

            {/* JSON Mode */}
            {inputMode === 'json' && (
                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">JSON Configuration</label>
                        <textarea
                            value={jsonInput}
                            onChange={(e) => setJsonInput(e.target.value)}
                            placeholder={getExampleConfig()}
                            className="w-full h-48 p-3 rounded-lg border bg-background font-mono text-sm resize-none"
                            disabled={loading}
                        />
                        <button
                            onClick={handleJSONSubmit}
                            disabled={loading || !jsonInput.trim()}
                            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Importing...
                                </>
                            ) : (
                                <>
                                    <FileJson className="w-4 h-4" />
                                    Import from JSON
                                </>
                            )}
                        </button>
                    </div>

                    {/* File Upload */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Or Upload JSON File</label>
                        <label className="w-full px-4 py-3 border-2 border-dashed rounded-lg hover:border-primary/50 transition-colors cursor-pointer flex items-center justify-center gap-2 text-muted-foreground hover:text-foreground">
                            <Upload className="w-5 h-5" />
                            <span>Click to upload JSON file</span>
                            <input
                                type="file"
                                accept=".json"
                                onChange={handleFileUpload}
                                className="hidden"
                                disabled={loading}
                            />
                        </label>
                    </div>
                </div>
            )}

            {/* Status Messages */}
            {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-destructive">
                    <XCircle className="w-5 h-5 flex-shrink-0" />
                    <span className="text-sm">{error}</span>
                </div>
            )}

            {success && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-2 text-green-600 dark:text-green-400">
                    <CheckCircle className="w-5 h-5 flex-shrink-0" />
                    <span className="text-sm">{success}</span>
                </div>
            )}
        </div>
    );
}
