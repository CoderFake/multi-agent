const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface MCPConfig {
    id: string;
    name: string;
    protocol: string;
    tools_count: number;
}

export interface MCPImportRequest {
    name?: string;
    protocol: string;
    config: Record<string, any>;
}

// Helper: build headers with optional Bearer token
function authHeaders(token?: string | null): HeadersInit {
    const h: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
}

export const api = {
    // MCP Management (no auth required)
    async importMCP(data: MCPImportRequest): Promise<MCPConfig> {
        const response = await fetch(`${API_URL}/api/mcp/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('Failed to import MCP');
        return response.json();
    },

    async importMCPFromFile(file: File): Promise<MCPConfig> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch(`${API_URL}/api/mcp/import/file`, {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) throw new Error('Failed to import MCP from file');
        return response.json();
    },

    async listMCPs(): Promise<MCPConfig[]> {
        const response = await fetch(`${API_URL}/api/mcp/list`);
        if (!response.ok) throw new Error('Failed to list MCPs');
        return response.json();
    },

    async getMCP(id: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/mcp/${id}`);
        if (!response.ok) throw new Error('Failed to get MCP');
        return response.json();
    },

    async deleteMCP(id: string): Promise<void> {
        const response = await fetch(`${API_URL}/api/mcp/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete MCP');
    },

    async getMCPTools(id: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/mcp/${id}/tools`);
        if (!response.ok) throw new Error('Failed to get MCP tools');
        return response.json();
    },

    async getMemories(token: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/memories`, {
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to get memories');
        return response.json();
    },

    async searchMemories(query: string, token: string, limit: number = 5): Promise<any> {
        const response = await fetch(`${API_URL}/api/memories/search`, {
            method: 'POST',
            headers: authHeaders(token),
            body: JSON.stringify({ query, limit }),
        });
        if (!response.ok) throw new Error('Failed to search memories');
        return response.json();
    },

    async addMemory(messages: object[], token: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/memories`, {
            method: 'POST',
            headers: authHeaders(token),
            body: JSON.stringify({ messages }),
        });
        if (!response.ok) throw new Error('Failed to add memory');
        return response.json();
    },

    async deleteMemory(memoryId: string, token: string): Promise<void> {
        const response = await fetch(`${API_URL}/api/memories/${encodeURIComponent(memoryId)}`, {
            method: 'DELETE',
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to delete memory');
    },

    async deleteAllMemories(token: string): Promise<void> {
        const response = await fetch(`${API_URL}/api/memories`, {
            method: 'DELETE',
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to delete all memories');
    },
};
