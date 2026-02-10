'use client';

import { useState, useRef, KeyboardEvent, ChangeEvent } from 'react';
import { Send, ChevronUp, Search, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

type ChatMode = 'chat' | 'research';

interface ChatInputWithModeProps {
    inProgress: boolean;
    onSend: (message: string, mode: ChatMode) => void;
    isDisabled?: boolean;
}

/**
 * Custom chat input with mode selector dropdown (Chat/Research)
 * Mode selector is positioned inside the input box (bottom-left corner)
 */
export function ChatInputWithMode({
    inProgress,
    onSend,
    isDisabled = false,
}: ChatInputWithModeProps) {
    const [mode, setMode] = useState<ChatMode>('chat');
    const [message, setMessage] = useState('');
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const modes = [
        { value: 'chat' as ChatMode, label: 'Chat', icon: MessageSquare, description: 'General conversation' },
        { value: 'research' as ChatMode, label: 'Research', icon: Search, description: 'Set as research question' },
    ];

    const currentMode = modes.find(m => m.value === mode)!;

    const handleSubmit = () => {
        if (message.trim() && !inProgress && !isDisabled) {
            onSend(message.trim(), mode);
            setMessage('');
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleModeChange = (newMode: ChatMode) => {
        setMode(newMode);
        setIsDropdownOpen(false);
        textareaRef.current?.focus();
    };

    return (
        <div className="p-4 border-t border-[#b8b8b8] bg-[#E0E9FD]">
            <div className="flex items-end gap-2">
                {/* Input Area with embedded mode selector */}
                <div className="flex-1 relative">
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={mode === 'research' 
                            ? "Enter your research question..." 
                            : "Type a message..."
                        }
                        disabled={inProgress || isDisabled}
                        className={cn(
                            "w-full min-h-[52px] max-h-[120px] pl-12 pr-4 py-3 rounded-xl",
                            "border bg-white resize-none",
                            "focus:outline-none focus:ring-2 focus:ring-[#6766FC]/50 focus:border-[#6766FC]",
                            "placeholder:text-gray-400 text-sm",
                            "disabled:opacity-50 disabled:cursor-not-allowed",
                            mode === 'research' && "border-[#6766FC]/30"
                        )}
                        rows={1}
                    />

                    {/* Mode Dropdown - positioned inside input (bottom-left) */}
                    <div className="absolute left-2 bottom-2">
                        <button
                            type="button"
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            className={cn(
                                "flex items-center justify-center w-8 h-8 rounded-lg transition-colors",
                                "hover:bg-gray-100",
                                mode === 'research' && "bg-[#6766FC]/10 text-[#6766FC] hover:bg-[#6766FC]/20"
                            )}
                            title={currentMode.label}
                        >
                            <currentMode.icon className="w-4 h-4" />
                            <ChevronUp className={cn(
                                "w-3 h-3 ml-0.5 transition-transform",
                                !isDropdownOpen && "rotate-180"
                            )} />
                        </button>

                        {/* Dropdown Menu */}
                        {isDropdownOpen && (
                            <>
                                <div 
                                    className="fixed inset-0 z-10" 
                                    onClick={() => setIsDropdownOpen(false)} 
                                />
                                <div className="absolute bottom-full mb-2 left-0 z-20 w-48 py-1 bg-white rounded-lg shadow-lg border border-gray-200">
                                    {modes.map((m) => (
                                        <button
                                            key={m.value}
                                            onClick={() => handleModeChange(m.value)}
                                            className={cn(
                                                "w-full flex items-start gap-3 px-3 py-2 text-left hover:bg-gray-50 transition-colors",
                                                mode === m.value && "bg-[#6766FC]/10"
                                            )}
                                        >
                                            <m.icon className={cn(
                                                "w-4 h-4 mt-0.5",
                                                mode === m.value ? "text-[#6766FC]" : "text-gray-500"
                                            )} />
                                            <div>
                                                <div className={cn(
                                                    "text-sm font-medium",
                                                    mode === m.value ? "text-[#6766FC]" : "text-gray-900"
                                                )}>
                                                    {m.label}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {m.description}
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Send Button */}
                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={!message.trim() || inProgress || isDisabled}
                    className={cn(
                        "flex items-center justify-center w-10 h-10 rounded-full transition-colors",
                        "bg-[#6766FC] text-white hover:bg-[#5554db]",
                        "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-[#6766FC]"
                    )}
                >
                    {inProgress ? (
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <Send className="w-4 h-4" />
                    )}
                </button>
            </div>
        </div>
    );
}

export type { ChatMode };
