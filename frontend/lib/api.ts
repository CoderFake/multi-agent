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

export const api = {
    // MCP Management
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
        const response = await fetch(`${API_URL}/api/mcp/${id}`, {
            method: 'DELETE',
        });
        if (!response.ok) throw new Error('Failed to delete MCP');
    },

    async getMCPTools(id: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/mcp/${id}/tools`);
        if (!response.ok) throw new Error('Failed to get MCP tools');
        return response.json();
    },

    // Chat
    getChatStreamURL(threadId: string = 'default'): string {
        return `${API_URL}/api/chat/stream`;
    },

    async getHistory(threadId: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/chat/history/${threadId}`);
        if (!response.ok) throw new Error('Failed to get chat history');
        return response.json();
    },

    async approveAction(threadId: string, approved: boolean): Promise<void> {
        const response = await fetch(`${API_URL}/api/chat/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: threadId, approved }),
        });
        if (!response.ok) throw new Error('Failed to approve action');
    },
};
