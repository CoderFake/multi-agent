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

    // ── Chat History ──────────────────────────────────────────────────

    async listChatSessions(token: string, limit = 50, offset = 0): Promise<any> {
        const response = await fetch(
            `${API_URL}/api/chat/sessions?limit=${limit}&offset=${offset}`,
            { headers: authHeaders(token) },
        );
        if (!response.ok) throw new Error('Failed to list chat sessions');
        return response.json();
    },

    async createChatSession(token: string, title?: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/chat/sessions`, {
            method: 'POST',
            headers: authHeaders(token),
            body: JSON.stringify({ title: title || null }),
        });
        if (!response.ok) throw new Error('Failed to create chat session');
        return response.json();
    },

    async getChatSession(sessionId: string, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/chat/sessions/${sessionId}`, {
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to get chat session');
        return response.json();
    },

    async updateChatSessionTitle(sessionId: string, title: string, token: string): Promise<void> {
        const response = await fetch(`${API_URL}/api/chat/sessions/${sessionId}`, {
            method: 'PATCH',
            headers: authHeaders(token),
            body: JSON.stringify({ title }),
        });
        if (!response.ok) throw new Error('Failed to update session title');
    },

    async deleteChatSession(sessionId: string, token: string): Promise<void> {
        const response = await fetch(`${API_URL}/api/chat/sessions/${sessionId}`, {
            method: 'DELETE',
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to delete chat session');
    },

    async deleteAllChatSessions(token: string): Promise<void> {
        const response = await fetch(`${API_URL}/api/chat/sessions`, {
            method: 'DELETE',
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to delete all sessions');
    },

    async addChatMessage(
        token: string,
        query: string,
        response?: string,
        sessionId?: string,
    ): Promise<any> {
        const res = await fetch(`${API_URL}/api/chat/messages`, {
            method: 'POST',
            headers: authHeaders(token),
            body: JSON.stringify({
                query,
                response: response || null,
                session_id: sessionId || null,
            }),
        });
        if (!res.ok) throw new Error('Failed to add chat message');
        return res.json();
    },

    async updateChatMessageResponse(
        messageId: string,
        responseText: string,
        token: string,
    ): Promise<void> {
        const res = await fetch(`${API_URL}/api/chat/messages/${messageId}`, {
            method: 'PATCH',
            headers: authHeaders(token),
            body: JSON.stringify({ response: responseText }),
        });
        if (!res.ok) throw new Error('Failed to update message response');
    },

    async getChatMessages(sessionId: string, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/api/chat/sessions/${sessionId}/messages`, {
            headers: authHeaders(token),
        });
        if (!response.ok) throw new Error('Failed to get messages');
        return response.json();
    },
};
