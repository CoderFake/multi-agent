'use client';

import { useCoAgentStateRender } from '@copilotkit/react-core';
import { Loader2, CheckCircle } from 'lucide-react';

interface ThinkingStep {
    type: 'analysis' | 'execution';
    message: string;
    status: 'active' | 'completed';
}

export function ThinkingDisplay() {
    useCoAgentStateRender({
        name: 'default',
        render: ({ state }) => {
            const thinkingStep = state?.thinking_step as ThinkingStep | undefined;

            if (!thinkingStep) {
                return null;
            }

            const getIcon = () => {
                if (thinkingStep.status === 'active') {
                    return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
                }
                return <CheckCircle className="h-4 w-4 text-green-500" />;
            };

            const getEmoji = () => {
                if (thinkingStep.type === 'analysis') {
                    return '🧠';
                }
                return '⚡';
            };

            return (
                <div className="flex items-center gap-2 px-4 py-2 bg-muted/50 border-l-4 border-blue-500 rounded-r-md animate-in slide-in-from-left duration-300">
                    {getIcon()}
                    <span className="text-sm">
                        <span className="mr-2">{getEmoji()}</span>
                        {thinkingStep.message}
                    </span>
                </div>
            );
        }
    });

    return null;
}
