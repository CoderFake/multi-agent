'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { CopilotChat, useCopilotChatSuggestions } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Settings, Search, MessageSquare, PanelRightClose, PanelRight } from 'lucide-react';
import { SettingsModal } from '@/components/SettingsModal';
import { ResearchCanvas, ResearchStateInfo } from '@/components/ResearchCanvas';
import { cn } from '@/lib/utils';

type ChatMode = 'chat' | 'research';

function ChatContent() {
    const [showSettings, setShowSettings] = useState(false);
    const [mode, setMode] = useState<ChatMode>('research');
    const [showResearchPanel, setShowResearchPanel] = useState(false);
    const [stateInfo, setStateInfo] = useState<ResearchStateInfo>({
        hasData: false,
        resourceCount: 0,
        hasReport: false,
    });

    // Auto show Research panel when data arrives
    useEffect(() => {
        if (stateInfo.hasData && !showResearchPanel) {
            setShowResearchPanel(true);
        }
    }, [stateInfo.hasData, showResearchPanel]);

    // Callback from ResearchCanvas to notify about state changes
    const handleStateChange = useCallback((info: ResearchStateInfo) => {
        setStateInfo(info);
    }, []);

    return (
        <>
            {/* Header with Settings */}
            <div className="flex h-[60px] bg-[#0E103D] text-white items-center px-10 justify-between">
                <h1 className="text-2xl font-medium">Research Assistant + MCP Tools</h1>
                <div className="flex items-center gap-2">
                    {stateInfo.hasData && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setShowResearchPanel(!showResearchPanel)}
                            className="text-white hover:bg-white/20"
                            title={showResearchPanel ? "Hide Research Panel" : "Show Research Panel"}
                        >
                            {showResearchPanel ? (
                                <PanelRightClose className="h-5 w-5" />
                            ) : (
                                <PanelRight className="h-5 w-5" />
                            )}
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowSettings(true)}
                        className="text-white hover:bg-white/20"
                    >
                        <Settings className="h-5 w-5" />
                    </Button>
                </div>
            </div>

            {/* Main Content */}
            <div
                className="flex flex-1 bg-gradient-to-br from-slate-50 to-slate-100"
                style={{ height: 'calc(100vh - 60px)' }}
            >
                {/* Chat Section - 70% centered when Research panel hidden */}
                <div
                    className={cn(
                        "h-full flex flex-col transition-all duration-300 ease-in-out",
                        showResearchPanel 
                            ? "w-[400px] flex-shrink-0" 
                            : "w-[70%] mx-auto"
                    )}
                    style={{
                        '--copilot-kit-background-color': '#FFFFFF',
                        '--copilot-kit-secondary-color': '#6766FC',
                        '--copilot-kit-separator-color': '#e5e7eb',
                        '--copilot-kit-primary-color': '#FFFFFF',
                        '--copilot-kit-contrast-color': '#000000',
                        '--copilot-kit-secondary-contrast-color': '#000',
                    } as any}
                >
                    {/* Mode Selector */}
                    <div className="flex items-center gap-2 px-4 py-3 bg-white border-b border-gray-200 shadow-sm">
                        <span className="text-xs text-gray-500 mr-1">Mode:</span>
                        <button
                            onClick={() => setMode('chat')}
                            className={cn(
                                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
                                mode === 'chat' 
                                    ? "bg-[#6766FC] text-white" 
                                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                            )}
                        >
                            <MessageSquare className="w-3.5 h-3.5" />
                            Chat
                        </button>
                        <button
                            onClick={() => setMode('research')}
                            className={cn(
                                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
                                mode === 'research' 
                                    ? "bg-[#6766FC] text-white" 
                                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                            )}
                        >
                            <Search className="w-3.5 h-3.5" />
                            Research
                        </button>
                    </div>

                    {/* Chat suggestions - only mounted after agent has context (avoids ZodError) */}
                    {stateInfo.hasData && <ChatSuggestions stateInfo={stateInfo} />}

                    {/* CopilotChat */}
                    <CopilotChat
                        className="flex-1"
                        labels={{
                            initial: mode === 'research' 
                                ? 'Research mode active. Ask a research question to get started.'
                                : 'Hi! I can help you with research and MCP tools.',
                        }}
                    />
                </div>

                {/* Research Canvas - ALWAYS mounted (hooks always active), hidden via CSS */}
                <div className={cn(
                    "flex-1 overflow-hidden border-l border-gray-200",
                    showResearchPanel 
                        ? "animate-in slide-in-from-right duration-300" 
                        : "hidden"
                )}>
                    <ResearchCanvas onStateChange={handleStateChange} />
                </div>
            </div>

            <SettingsModal
                isOpen={showSettings}
                onClose={() => setShowSettings(false)}
            />
        </>
    );
}

/**
 * Chat suggestions — mounted as separate component so it can be
 * conditionally rendered (avoids ZodError for threadId/runId on initial load).
 * Renders suggestion chips inside CopilotChat's message area.
 */
function ChatSuggestions({ stateInfo }: { stateInfo: ResearchStateInfo }) {
    useCopilotChatSuggestions(
        {
            instructions: `Based on the current research state, suggest relevant next actions.
                ${stateInfo.researchQuestion ? `Current research question: "${stateInfo.researchQuestion}"` : "No research question set yet. Suggest a research topic."}
                ${stateInfo.resourceCount > 0 ? `Has ${stateInfo.resourceCount} resources gathered.` : "No resources yet."}
                ${stateInfo.hasReport ? "Has a research draft. Suggest improvements or follow-up questions." : "No research draft yet."}`,
        },
        [stateInfo.researchQuestion, stateInfo.resourceCount, stateInfo.hasReport]
    );
    return null;
}

export default function Home() {
    return (
        <CopilotKit runtimeUrl="/api/copilotkit" showDevConsole={false}>
            <ChatContent />
        </CopilotKit>
    );
}
