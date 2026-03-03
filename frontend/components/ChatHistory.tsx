'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { MessageSquare, Plus, Trash2, X, Pencil, Check, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatSession {
    id: string;
    title: string | null;
    created_at: string | null;
    updated_at: string | null;
    message_count: number;
}

interface ChatHistoryProps {
    token: string;
    isOpen: boolean;
    onClose: () => void;
    onSelectSession: (sessionId: string) => void;
    onNewChat: () => void;
    activeSessionId?: string | null;
    refreshTrigger?: number;
}

export function ChatHistory({
    token,
    isOpen,
    onClose,
    onSelectSession,
    onNewChat,
    activeSessionId,
    refreshTrigger,
}: ChatHistoryProps) {
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [loading, setLoading] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState('');
    const tokenRef = useRef(token);
    tokenRef.current = token;

    const loadSessions = useCallback(async () => {
        const t = tokenRef.current;
        if (!t) return;
        setLoading(true);
        try {
            const data = await api.listChatSessions(t);
            setSessions(data.sessions || []);
        } catch (err) {
            console.error('Failed to load sessions:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    const prevIsOpen = useRef(false);
    useEffect(() => {
        if (isOpen && !prevIsOpen.current) loadSessions();
        prevIsOpen.current = isOpen;
    }, [isOpen, loadSessions]);

    useEffect(() => {
        if (refreshTrigger && refreshTrigger > 0) loadSessions();
    }, [refreshTrigger]);

    const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        if (!confirm('Delete this conversation?')) return;
        try {
            await api.deleteChatSession(sessionId, token);
            setSessions((prev) => prev.filter((s) => s.id !== sessionId));
            if (activeSessionId === sessionId) onNewChat();
        } catch (err) {
            console.error('Failed to delete session:', err);
        }
    };

    const handleStartEdit = (e: React.MouseEvent, session: ChatSession) => {
        e.stopPropagation();
        setEditingId(session.id);
        setEditTitle(session.title || '');
    };

    const handleSaveEdit = async (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        if (!editTitle.trim()) return;
        try {
            await api.updateChatSessionTitle(sessionId, editTitle.trim(), token);
            setSessions((prev) =>
                prev.map((s) => (s.id === sessionId ? { ...s, title: editTitle.trim() } : s))
            );
        } catch (err) {
            console.error('Failed to rename:', err);
        } finally {
            setEditingId(null);
        }
    };

    const handleDeleteAll = async () => {
        if (!confirm('Delete ALL conversations? This cannot be undone.')) return;
        try {
            await api.deleteAllChatSessions(token);
            setSessions([]);
            onNewChat();
        } catch (err) {
            console.error('Failed to delete all:', err);
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now.getTime() - d.getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString();
    };

    if (!isOpen) return null;

    return (
        <div className="h-full flex flex-col bg-white border-r border-gray-200 w-[280px] flex-shrink-0">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <h2 className="text-sm font-semibold text-gray-700">Chat History</h2>
                <div className="flex items-center gap-1">
                    {sessions.length > 0 && (
                        <button
                            onClick={handleDeleteAll}
                            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                            title="Delete all"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* New Chat button */}
            <div className="px-3 py-2">
                <button
                    onClick={() => {
                        onNewChat();
                        loadSessions();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-[#6766FC] bg-[#6766FC]/5 hover:bg-[#6766FC]/10 rounded-lg transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    New Chat
                </button>
            </div>

            {/* Session list */}
            <div className="flex-1 overflow-y-auto px-2 py-1">
                {loading ? (
                    <div className="flex items-center justify-center py-8 text-gray-400 text-sm">
                        Loading…
                    </div>
                ) : sessions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                        <MessageSquare className="w-8 h-8 mb-2 opacity-40" />
                        <p className="text-sm">No conversations yet</p>
                    </div>
                ) : (
                    sessions.map((session) => (
                        <div
                            key={session.id}
                            onClick={() => onSelectSession(session.id)}
                            className={cn(
                                'group flex items-start gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors mb-0.5',
                                activeSessionId === session.id
                                    ? 'bg-[#6766FC]/10 text-[#6766FC]'
                                    : 'hover:bg-gray-50 text-gray-700'
                            )}
                        >
                            <MessageSquare className="w-4 h-4 mt-0.5 flex-shrink-0 opacity-50" />
                            <div className="flex-1 min-w-0">
                                {editingId === session.id ? (
                                    <div className="flex items-center gap-1">
                                        <input
                                            value={editTitle}
                                            onChange={(e) => setEditTitle(e.target.value)}
                                            onClick={(e) => e.stopPropagation()}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') handleSaveEdit(e as any, session.id);
                                                if (e.key === 'Escape') setEditingId(null);
                                            }}
                                            className="flex-1 text-sm bg-white border border-gray-300 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-[#6766FC]"
                                            autoFocus
                                        />
                                        <button
                                            onClick={(e) => handleSaveEdit(e, session.id)}
                                            className="p-0.5 text-green-600 hover:bg-green-50 rounded"
                                        >
                                            <Check className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                ) : (
                                    <>
                                        <p className="text-sm font-medium truncate">
                                            {session.title || 'Untitled'}
                                        </p>
                                        <div className="flex items-center gap-1 mt-0.5">
                                            <Clock className="w-3 h-3 text-gray-400" />
                                            <span className="text-xs text-gray-400">
                                                {formatDate(session.updated_at || session.created_at)}
                                            </span>
                                            {session.message_count > 0 && (
                                                <span className="text-xs text-gray-400 ml-1">
                                                    · {session.message_count} msg{session.message_count !== 1 ? 's' : ''}
                                                </span>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Action buttons (visible on hover) */}
                            {editingId !== session.id && (
                                <div className="hidden group-hover:flex items-center gap-0.5 flex-shrink-0">
                                    <button
                                        onClick={(e) => handleStartEdit(e, session)}
                                        className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                                        title="Rename"
                                    >
                                        <Pencil className="w-3 h-3" />
                                    </button>
                                    <button
                                        onClick={(e) => handleDelete(e, session.id)}
                                        className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
