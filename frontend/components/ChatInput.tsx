'use client';

import { Button } from '@/components/ui/button';
import { Send, StopCircle, RotateCcw, Paperclip } from 'lucide-react';
import { KeyboardEvent, ChangeEvent, FormEvent } from 'react';

interface ChatInputProps {
    input: string;
    handleInputChange: (e: ChangeEvent<HTMLTextAreaElement>) => void;
    handleSubmit: (e: FormEvent) => void;
    isLoading?: boolean;
    isErrored?: boolean;
    errorMessage?: string;
    stop?: () => void;
    retry?: () => void;
    children?: React.ReactNode;
}

export function ChatInput({
    input,
    handleInputChange,
    handleSubmit,
    isLoading = false,
    isErrored = false,
    errorMessage,
    stop,
    retry,
    children,
}: ChatInputProps) {
    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isLoading && input.trim()) {
                handleSubmit(e as any);
            }
        }
    };

    return (
        <div className="border-t bg-background">
            {errorMessage && (
                <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
                    {errorMessage}
                </div>
            )}
            
            <div className="max-w-3xl mx-auto px-4 py-4">
                <form onSubmit={handleSubmit} className="relative">
                    <div className="flex items-end gap-2">
                        <div className="flex-1 relative">
                            <textarea
                                value={input}
                                onChange={handleInputChange}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask me anything..."
                                className="w-full min-h-[52px] max-h-[200px] px-4 py-3 pr-12 rounded-2xl border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                                rows={1}
                                disabled={isLoading}
                            />
                            
                            {children && (
                                <div className="absolute bottom-3 right-3">
                                    {children}
                                </div>
                            )}
                        </div>

                        {isLoading ? (
                            <Button
                                type="button"
                                size="icon"
                                variant="destructive"
                                onClick={stop}
                                className="rounded-full h-12 w-12 flex-shrink-0"
                            >
                                <StopCircle className="h-5 w-5" />
                            </Button>
                        ) : isErrored && retry ? (
                            <Button
                                type="button"
                                size="icon"
                                variant="outline"
                                onClick={retry}
                                className="rounded-full h-12 w-12 flex-shrink-0"
                            >
                                <RotateCcw className="h-5 w-5" />
                            </Button>
                        ) : (
                            <Button
                                type="submit"
                                size="icon"
                                disabled={!input.trim() || isLoading}
                                className="rounded-full h-12 w-12 flex-shrink-0"
                            >
                                <Send className="h-5 w-5" />
                            </Button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
