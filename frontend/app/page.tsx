'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { CopilotChat, useCopilotChatSuggestions } from '@copilotkit/react-ui';
import { useLangGraphInterrupt } from '@copilotkit/react-core';
import '@copilotkit/react-ui/styles.css';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Settings, ChevronLeft, ChevronRight, Brain, LogOut, CheckCircle, XCircle, Terminal } from 'lucide-react';
import { SettingsModal } from '@/components/SettingsModal';
import { ResearchCanvas, ResearchStateInfo } from '@/components/ResearchCanvas';
import { CustomChatInput, ResearchModeContext } from '@/components/CustomChatInput';
import { MemoryPanel } from '@/components/MemoryPanel';
import { LoginPage } from '@/components/LoginPage';
import { useAuth } from '@/lib/auth-context';
import { cn } from '@/lib/utils';

// ── HITL: Tool Approval Card ─────────────────────────────────────────
interface ApprovalCardProps {
    toolName: string;
    argsPreview: string;
    onApprove: () => void;
    onReject: () => void;
}

function ApprovalCard({ toolName, argsPreview, onApprove, onReject }: ApprovalCardProps) {
    return (
        <div className="mx-4 my-2 rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
            <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
                    <Terminal className="h-4 w-4 text-amber-600" />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-amber-900">Action requires approval</p>
                    <p className="text-xs text-amber-700 mt-0.5">
                        The agent wants to run <code className="font-mono bg-amber-100 px-1 py-0.5 rounded">{toolName}</code>
                    </p>
                    {argsPreview && argsPreview !== '{}' && (
                        <pre className="mt-2 text-xs text-amber-800 bg-amber-100 rounded-lg p-2 overflow-x-auto whitespace-pre-wrap break-all">
                            {argsPreview}
                        </pre>
                    )}
                </div>
            </div>
            <div className="flex gap-2 mt-3">
                <button
                    onClick={onApprove}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-[#6766FC] hover:bg-[#5554e0] text-white text-sm font-medium rounded-lg transition-colors"
                >
                    <CheckCircle className="h-4 w-4" />
                    Approve
                </button>
                <button
                    onClick={onReject}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 border border-gray-200 hover:bg-red-50 hover:border-red-200 hover:text-red-600 text-gray-600 text-sm font-medium rounded-lg transition-colors"
                >
                    <XCircle className="h-4 w-4" />
                    Reject
                </button>
            </div>
        </div>
    );
}

// ── Main Chat UI (rendered when authenticated) ───────────────────────
function ChatContent({ token }: { token: string }) {
    const { user, signOut } = useAuth();
    const [showSettings, setShowSettings] = useState(false);
    const [researchMode, setResearchMode] = useState(true);
    const [hasInteracted, setHasInteracted] = useState(false);
    const [showResearchPanel, setShowResearchPanel] = useState(false);
    const [showMemoryPanel, setShowMemoryPanel] = useState(false);
    const [stateInfo, setStateInfo] = useState<ResearchStateInfo>({
        hasData: false,
        resourceCount: 0,
        hasReport: false,
    });

    const prevHasData = useRef(false);
    useEffect(() => {
        if (stateInfo.hasData && !prevHasData.current) setShowResearchPanel(true);
        prevHasData.current = stateInfo.hasData;
    }, [stateInfo.hasData]);

    const handleStateChange = useCallback((info: ResearchStateInfo) => {
        setStateInfo(info);
    }, []);

    // ── HITL: intercept approval interrupts ──────────────────────────
    useLangGraphInterrupt({
        enabled: ({ eventValue }) => eventValue?.type === 'approval',
        render: ({ event, resolve }) => (
            <ApprovalCard
                toolName={event.value.tool_name ?? 'unknown'}
                argsPreview={event.value.args_preview ?? ''}
                onApprove={() => resolve('approved')}
                onReject={() => resolve('rejected')}
            />
        ),
    });

    return (
        <ResearchModeContext.Provider value={{ researchMode, setResearchMode, hasInteracted, setHasInteracted }}>
            <div className="h-screen flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex h-[60px] flex-shrink-0 bg-white text-gray-800 items-center px-10 justify-between border-b border-gray-100">
                    <h1 className="text-2xl font-medium">Assistant</h1>
                    <div className="flex items-center gap-2">
                        {user?.displayName && (
                            <span className="text-sm text-gray-500">{user.displayName}</span>
                        )}
                        <Button variant="ghost" size="icon"
                            onClick={() => setShowMemoryPanel(!showMemoryPanel)}
                            className={cn("text-gray-800 hover:bg-[#f0f0ff]", showMemoryPanel && "bg-[#ededff] text-[#6766FC]")}
                            title="Memory">
                            <Brain className="h-5 w-5" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => setShowSettings(true)}
                            className="text-gray-800 hover:bg-gray-100">
                            <Settings className="h-5 w-5" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={signOut}
                            className="text-gray-800 hover:bg-red-50 hover:text-red-500" title="Sign out">
                            <LogOut className="h-5 w-5" />
                        </Button>
                    </div>
                </div>

                {/* Main content */}
                <div className="relative flex flex-1 min-h-0 bg-white">
                    <div
                        className={cn(
                            "h-full min-h-0 flex flex-col overflow-hidden transition-all duration-300 ease-in-out",
                            showResearchPanel ? "w-[400px] flex-shrink-0" : "w-[70%] mx-auto",
                            !hasInteracted && "justify-center",
                        )}
                        style={{
                            '--copilot-kit-background-color': '#FFFFFF',
                            '--copilot-kit-secondary-color': '#6766FC',
                            '--copilot-kit-separator-color': '#e5e7eb',
                            '--copilot-kit-secondary-contrast-color': '#000',
                        } as any}
                    >
                        {stateInfo.hasData && <ChatSuggestions stateInfo={stateInfo} />}
                        <CopilotChat
                            className={hasInteracted ? "flex-1 min-h-0" : ""}
                            Input={CustomChatInput}
                            labels={{ initial: "" }}
                        />
                    </div>

                    {stateInfo.hasData && (
                        <button
                            onClick={() => setShowResearchPanel(!showResearchPanel)}
                            className={cn(
                                "absolute right-0 top-1/2 -translate-y-1/2 translate-x-[-50%] z-30",
                                "w-6 h-10 flex items-center justify-center",
                                "bg-white border border-gray-200 rounded-md shadow-sm hover:bg-gray-50 transition-colors",
                                showResearchPanel && "hidden",
                            )}>
                            <ChevronLeft className="h-4 w-4 text-gray-500" />
                        </button>
                    )}

                    <div className={cn("relative h-full transition-all duration-300 overflow-visible", showResearchPanel ? "flex-1 min-w-0" : "w-0")}>
                        {stateInfo.hasData && showResearchPanel && (
                            <button onClick={() => setShowResearchPanel(false)}
                                className="absolute top-1/2 -translate-y-1/2 -left-3 z-30 w-6 h-10 flex items-center justify-center bg-white border border-gray-200 rounded-md shadow-sm hover:bg-gray-50">
                                <ChevronRight className="h-4 w-4 text-gray-500" />
                            </button>
                        )}
                        <div className={cn("h-full overflow-hidden border-l border-gray-200", showResearchPanel ? "animate-in slide-in-from-right duration-300" : "invisible border-l-0")}>
                            <ResearchCanvas onStateChange={handleStateChange} />
                        </div>
                    </div>
                </div>

                <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />
                <MemoryPanel token={token} isOpen={showMemoryPanel} onClose={() => setShowMemoryPanel(false)} />
            </div>
        </ResearchModeContext.Provider>
    );
}

function ChatSuggestions({ stateInfo }: { stateInfo: ResearchStateInfo }) {
    useCopilotChatSuggestions(
        {
            instructions: `Based on the current research state, suggest relevant next actions.
                ${stateInfo.researchQuestion ? `Current research question: "${stateInfo.researchQuestion}"` : "No research question set yet."}
                ${stateInfo.resourceCount > 0 ? `Has ${stateInfo.resourceCount} resources gathered.` : "No resources yet."}
                ${stateInfo.hasReport ? "Has a research draft." : "No draft yet."}`,
        },
        [stateInfo.researchQuestion, stateInfo.resourceCount, stateInfo.hasReport],
    );
    return null;
}

// ── Root page: login gate ─────────────────────────────────────────────
export default function Home() {
    const { user, loading, getIdToken } = useAuth();
    const [token, setToken] = useState<string | null>(null);

    useEffect(() => {
        if (user) {
            getIdToken().then(setToken);
        } else {
            setToken(null);
        }
    }, [user, getIdToken]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
                Loading…
            </div>
        );
    }

    if (!user || !token) return <LoginPage />;

    return (
        <CopilotKit
            runtimeUrl="/api/copilotkit"
            showDevConsole={false}
            // Token forwarded as forwarded_props.authorization (CopilotKit self-hosted pattern)
            properties={{ authorization: token }}
        >
            <ChatContent token={token} />
        </CopilotKit>
    );
}
