'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { CopilotChat, useCopilotChatSuggestions } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import { SettingsModal } from '@/components/SettingsModal';
import { ResearchCanvas, ResearchStateInfo } from '@/components/ResearchCanvas';
import { CustomChatInput, ResearchModeContext } from '@/components/CustomChatInput';
import { cn } from '@/lib/utils';

function ChatContent() {
    const [showSettings, setShowSettings] = useState(false);
    const [researchMode, setResearchMode] = useState(true);
    const [hasInteracted, setHasInteracted] = useState(false);
    const [showResearchPanel, setShowResearchPanel] = useState(false);
    const [stateInfo, setStateInfo] = useState<ResearchStateInfo>({
        hasData: false,
        resourceCount: 0,
        hasReport: false,
    });

    // Auto show Research panel only when hasData transitions from false → true
    const prevHasData = useRef(false);
    useEffect(() => {
        if (stateInfo.hasData && !prevHasData.current) {
            setShowResearchPanel(true);
        }
        prevHasData.current = stateInfo.hasData;
    }, [stateInfo.hasData]);

    // Callback from ResearchCanvas to notify about state changes
    const handleStateChange = useCallback((info: ResearchStateInfo) => {
        setStateInfo(info);
    }, []);

    return (
        <ResearchModeContext.Provider value={{ researchMode, setResearchMode, hasInteracted, setHasInteracted }}>
            <div className="h-screen flex flex-col overflow-hidden">
                {/* Header with Settings */}
                <div className="flex h-[60px] flex-shrink-0 bg-white text-gray-800 items-center px-10 justify-between">
                    <h1 className="text-2xl font-medium">Assistant</h1>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setShowSettings(true)}
                            className="text-gray-800 hover:bg-gray-100"
                        >
                            <Settings className="h-5 w-5" />
                        </Button>
                    </div>
                </div>

                {/* Main Content — fills remaining height, no outer scroll */}
                <div className="relative flex flex-1 min-h-0 bg-white from-slate-50 to-slate-100">
                    {/* Chat Section */}
                    <div
                        className={cn(
                            "h-full min-h-0 flex flex-col overflow-hidden transition-all duration-300 ease-in-out",
                            showResearchPanel
                                ? "w-[400px] flex-shrink-0"
                                : "w-[70%] mx-auto",
                            !hasInteracted && "justify-center"
                        )}
                        style={{
                            '--copilot-kit-background-color': '#FFFFFF',
                            '--copilot-kit-secondary-color': '#6766FC',
                            '--copilot-kit-separator-color': '#e5e7eb',
                            '--copilot-kit-secondary-contrast-color': '#000',
                        } as any}
                    >
                        {/* Chat suggestions - only mounted after agent has context */}
                        {stateInfo.hasData && <ChatSuggestions stateInfo={stateInfo} />}

                        {/* CopilotChat — fills space after interaction, shrinks to content when empty */}
                        <CopilotChat
                            className={hasInteracted ? "flex-1 min-h-0" : ""}
                            Input={CustomChatInput}
                            labels={{ initial: "" }}
                        />
                    </div>

                    {/* Chevron toggle — always outside artifact wrapper so it's never clipped */}
                    {stateInfo.hasData && (
                        <button
                            onClick={() => setShowResearchPanel(!showResearchPanel)}
                            className={cn(
                                "absolute right-0 top-1/2 -translate-y-1/2 translate-x-[-50%] z-30",
                                "w-6 h-10 flex items-center justify-center",
                                "bg-white border border-gray-200 rounded-md shadow-sm",
                                "hover:bg-gray-50 transition-colors",
                                showResearchPanel && "hidden"
                            )}
                            title="Show Research Panel"
                        >
                            <ChevronLeft className="h-4 w-4 text-gray-500" />
                        </button>
                    )}

                    {/* Research Canvas - ALWAYS mounted (hooks always active), collapsed via width */}
                    <div className={cn(
                        "relative h-full transition-all duration-300 ease-in-out overflow-visible",
                        showResearchPanel ? "flex-1 min-w-0" : "w-0"
                    )}>
                        {/* Chevron toggle — centered vertically on the left edge of artifact (when open) */}
                        {stateInfo.hasData && showResearchPanel && (
                            <button
                                onClick={() => setShowResearchPanel(false)}
                                className={cn(
                                    "absolute top-1/2 -translate-y-1/2 -left-3 z-30",
                                    "w-6 h-10 flex items-center justify-center",
                                    "bg-white border border-gray-200 rounded-md shadow-sm",
                                    "hover:bg-gray-50 transition-colors"
                                )}
                                title="Hide Research Panel"
                            >
                                <ChevronRight className="h-4 w-4 text-gray-500" />
                            </button>
                        )}
                        <div className={cn(
                            "h-full overflow-hidden border-l border-gray-200",
                            showResearchPanel
                                ? "animate-in slide-in-from-right duration-300"
                                : "invisible border-l-0"
                        )}>
                            <ResearchCanvas onStateChange={handleStateChange} />
                        </div>
                    </div>
                </div>

                <SettingsModal
                    isOpen={showSettings}
                    onClose={() => setShowSettings(false)}
                />
            </div>
        </ResearchModeContext.Provider>
    );
}

/**
 * Chat suggestions — mounted as separate component so it can be
 * conditionally rendered (avoids ZodError for threadId/runId on initial load).
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
