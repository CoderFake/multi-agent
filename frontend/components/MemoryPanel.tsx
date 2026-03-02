'use client';

import { useState, useEffect, useCallback } from 'react';
import { Brain, Trash2, Search, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

interface MemoryItem {
    id: string;
    memory: string;
    created_at?: string;
    updated_at?: string;
    score?: number;
    categories?: string[];
}

interface MemoryPanelProps {
    userId?: string;
    isOpen: boolean;
    onClose: () => void;
}

export function MemoryPanel({ userId = 'default_user', isOpen, onClose }: MemoryPanelProps) {
    const [memories, setMemories] = useState<MemoryItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<MemoryItem[] | null>(null);

    const fetchMemories = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.getMemories(userId);
            setMemories(data.memories || []);
        } catch (err) {
            console.error('Failed to fetch memories:', err);
        } finally {
            setLoading(false);
        }
    }, [userId]);

    useEffect(() => {
        if (isOpen) {
            fetchMemories();
        }
    }, [isOpen, fetchMemories]);

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            setSearchResults(null);
            return;
        }
        setLoading(true);
        try {
            const data = await api.searchMemories(searchQuery, userId);
            setSearchResults(data.results || []);
        } catch (err) {
            console.error('Failed to search memories:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (memoryId: string) => {
        try {
            await api.deleteMemory(memoryId);
            setMemories(prev => prev.filter(m => m.id !== memoryId));
            if (searchResults) {
                setSearchResults(prev => prev!.filter(m => m.id !== memoryId));
            }
        } catch (err) {
            console.error('Failed to delete memory:', err);
        }
    };

    const handleDeleteAll = async () => {
        if (!confirm('Delete all memories? This cannot be undone.')) return;
        try {
            await api.deleteAllMemories(userId);
            setMemories([]);
            setSearchResults(null);
        } catch (err) {
            console.error('Failed to delete all memories:', err);
        }
    };

    const displayList = searchResults ?? memories;

    if (!isOpen) return null;

    return (
        <div className="fixed inset-y-0 right-0 w-[380px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100" style={{ background: 'linear-gradient(to right, #f0f0ff, #ededff)' }}>
                <div className="flex items-center gap-2">
                    <Brain className="h-5 w-5" style={{ color: '#6766FC' }} />
                    <h2 className="text-lg font-semibold text-gray-800">Memory</h2>
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: '#ededff', color: '#6766FC' }}>
                        {memories.length}
                    </span>
                </div>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={fetchMemories}
                        className="h-8 w-8 text-gray-500 hover:text-[#6766FC]"
                        title="Refresh"
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="h-8 w-8 text-gray-500 hover:text-gray-700"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Search */}
            <div className="px-4 py-3 border-b border-gray-100">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search memories..."
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                if (!e.target.value.trim()) setSearchResults(null);
                            }}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:border-[#6766FC]"
                            style={{ '--tw-ring-color': '#6766FC33' } as any}
                        />
                    </div>
                    <Button
                        onClick={handleSearch}
                        size="sm"
                        className="text-white px-3"
                        style={{ backgroundColor: '#6766FC' }}
                    >
                        Search
                    </Button>
                </div>
                {searchResults && (
                    <button
                        onClick={() => { setSearchResults(null); setSearchQuery(''); }}
                        className="mt-2 text-xs hover:underline"
                        style={{ color: '#6766FC' }}
                    >
                        ← Back to all memories
                    </button>
                )}
            </div>

            {/* Memory List */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
                {loading && displayList.length === 0 ? (
                    <div className="flex items-center justify-center py-12 text-gray-400">
                        <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                        Loading...
                    </div>
                ) : displayList.length === 0 ? (
                    <div className="text-center py-12">
                        <Brain className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                        <p className="text-sm text-gray-500">
                            {searchResults ? 'No matching memories found' : 'No memories yet'}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                            Memories are automatically created from conversations
                        </p>
                    </div>
                ) : (
                    displayList.map((item) => (
                        <div
                            key={item.id}
                            className="group relative p-3 bg-gray-50 rounded-lg border border-gray-100 transition-colors"
                            style={{ '--hover-bg': '#f5f5ff', '--hover-border': '#d5d5fc' } as any}
                            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#f5f5ff'; e.currentTarget.style.borderColor = '#d5d5fc'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; e.currentTarget.style.borderColor = ''; }}
                        >
                            <p className="text-sm text-gray-700 pr-8 leading-relaxed">
                                {item.memory}
                            </p>
                            <div className="flex items-center gap-2 mt-2">
                                {item.score && (
                                    <span className="text-xs text-gray-400">
                                        Score: {(item.score * 100).toFixed(0)}%
                                    </span>
                                )}
                                {item.created_at && (
                                    <span className="text-xs text-gray-400">
                                        {new Date(item.created_at).toLocaleDateString()}
                                    </span>
                                )}
                                {item.categories?.map(cat => (
                                    <span key={cat} className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: '#ededff', color: '#6766FC' }}>
                                        {cat}
                                    </span>
                                ))}
                            </div>
                            <button
                                onClick={() => handleDelete(item.id)}
                                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 rounded"
                                title="Delete memory"
                            >
                                <Trash2 className="h-3.5 w-3.5 text-red-500" />
                            </button>
                        </div>
                    ))
                )}
            </div>

            {/* Footer */}
            {memories.length > 0 && (
                <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeleteAll}
                        className="w-full text-red-500 hover:text-red-700 hover:bg-red-50 text-xs"
                    >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Delete All Memories
                    </Button>
                </div>
            )}
        </div>
    );
}

