'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { CopilotChat } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Settings } from 'lucide-react';
import { SettingsModal } from '@/components/SettingsModal';
import { useCoAgent } from '@copilotkit/react-core';
import { useCopilotChatSuggestions } from '@copilotkit/react-ui';
import { ResearchCanvas } from '@/components/ResearchCanvas';
import { AgentState } from '@/lib/types';

function ChatContent() {
    const [showSettings, setShowSettings] = useState(false);

    // Setup agent state - research-canvas pattern + MCP fields
    const { state, setState } = useCoAgent<AgentState>({
        name: 'default',
        initialState: {
            model: 'gpt-4-turbo-preview',
            research_question: '',
            resources: [],
            report: '',
            logs: [],
        }
    });

    // Add chat suggestions
    useCopilotChatSuggestions({
        instructions: 'Suggest helpful actions: research topics, MCP tools, or data analysis',
        maxSuggestions: 3
    });

    return (
        <>
            {/* Header with Settings */}
            <div className="flex h-[60px] bg-[#0E103D] text-white items-center px-10 justify-between">
                <h1 className="text-2xl font-medium">Research Assistant + MCP Tools</h1>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowSettings(true)}
                    className="text-white hover:bg-white/20"
                >
                    <Settings className="h-5 w-5" />
                </Button>
            </div>

            {/* Split View: ResearchCanvas + Chat */}
            <div
                className="flex flex-1 border"
                style={{ height: 'calc(100vh - 60px)' }}
            >
                {/* Left: Research Canvas */}
                <div className="flex-1 overflow-hidden">
                    <ResearchCanvas />
                </div>

                {/* Right: Copilot Chat */}
                <div
                    className="w-[500px] h-full flex-shrink-0"
                    style={{
                        '--copilot-kit-background-color': '#E0E9FD',
                        '--copilot-kit-secondary-color': '#6766FC',
                        '--copilot-kit-separator-color': '#b8b8b8',
                        '--copilot-kit-primary-color': '#FFFFFF',
                        '--copilot-kit-contrast-color': '#000000',
                        '--copilot-kit-secondary-contrast-color': '#000',
                    } as any}
                >
                    <CopilotChat
                        className="h-full"
                        onSubmitMessage={async (message) => {
                            // Clear logs before starting new research/task
                            setState({ ...state, logs: [] });
                            await new Promise((resolve) => setTimeout(resolve, 30));
                        }}
                        labels={{
                            initial: 'Hi! I can help you with research and MCP tools.',
                        }}
                    />
                </div>
            </div>

            <SettingsModal
                isOpen={showSettings}
                onClose={() => setShowSettings(false)}
            />
        </>
    );
}

export default function Home() {
    return (
        <CopilotKit runtimeUrl="/api/copilotkit" showDevConsole={false}>
            <ChatContent />
        </CopilotKit>
    );
}