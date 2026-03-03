'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { CopilotChat, useCopilotChatSuggestions } from '@copilotkit/react-ui';
import { useLangGraphInterrupt } from '@copilotkit/react-core';
import '@copilotkit/react-ui/styles.css';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Settings, ChevronLeft, ChevronRight, Brain, LogOut, CheckCircle, XCircle, Terminal, History } from 'lucide-react';
import { SettingsModal } from '@/components/SettingsModal';
import { ResearchCanvas, ResearchStateInfo } from '@/components/ResearchCanvas';
import { CustomChatInput, ResearchModeContext, UploadedDoc } from '@/components/CustomChatInput';
import { MemoryPanel } from '@/components/MemoryPanel';
import { ChatHistory } from '@/components/ChatHistory';
import { LoginPage } from '@/components/LoginPage';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useChatPersistence } from '@/lib/use-chat-persistence';

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
function ChatContent({ token, researchMode, setResearchMode, refreshToken }: { token: string; researchMode: boolean; setResearchMode: (v: boolean) => void; refreshToken: (force?: boolean) => Promise<string | null> }) {
    const { user, signOut } = useAuth();
    const [showSettings, setShowSettings] = useState(false);
    const [hasInteracted, setHasInteracted] = useState(false);
    const [showResearchPanel, setShowResearchPanel] = useState(false);
    const [showMemoryPanel, setShowMemoryPanel] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [chatKey, setChatKey] = useState(0);
    const [sidebarRefresh, setSidebarRefresh] = useState(0);
    const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
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

    const handleNewChat = useCallback(() => {
        setActiveSessionId(null);
        setHasInteracted(false);
        setChatKey((k) => k + 1);
    }, []);

    const handleSelectSession = useCallback(async (sessionId: string) => {
        setActiveSessionId(sessionId);
        setHasInteracted(true);
        setChatKey((k) => k + 1);
    }, []);

    // ── Auto-save chat messages to DB ────────────────────────────────
    const handleSessionCreated = useCallback((sessionId: string, title: string | null) => {
        setActiveSessionId(sessionId);
        setSidebarRefresh((n) => n + 1);
    }, []);

    useChatPersistence({
        token,
        activeSessionId,
        onSessionCreated: handleSessionCreated,
    });

    // ── Handle CopilotKit errors (auto-refresh token on 401) ─────────
    const handleCopilotError = useCallback(async (errorEvent: any) => {
        const status = errorEvent?.context?.response?.status
            ?? errorEvent?.error?.status
            ?? (typeof errorEvent?.error?.message === 'string' && errorEvent.error.message.includes('401') ? 401 : 0);
        if (status === 401) {
            console.warn('[CopilotKit] 401 detected — refreshing token…');
            await refreshToken(true);
        }
    }, [refreshToken]);

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
        <ResearchModeContext.Provider value={{ researchMode, setResearchMode, hasInteracted, setHasInteracted, uploadedDocs, setUploadedDocs }}>
            <div className="h-screen flex overflow-hidden">
                {/* ── Left Sidebar (ChatGPT-style) ──────────────────────── */}
                <div
                    className={cn(
                        "h-full flex-shrink-0 bg-[#f9f9f9] transition-all duration-300 ease-in-out overflow-hidden border-r border-gray-200",
                        sidebarOpen ? "w-[260px]" : "w-0"
                    )}
                >
                    <ChatHistory
                        token={token}
                        isOpen={sidebarOpen}
                        onClose={() => setSidebarOpen(false)}
                        onSelectSession={handleSelectSession}
                        onNewChat={handleNewChat}
                        activeSessionId={activeSessionId}
                        refreshTrigger={sidebarRefresh}
                    />
                </div>

                {/* ── Main Area ──────────────────────────────────────────── */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Header */}
                    <div className="flex h-[60px] flex-shrink-0 bg-white text-gray-800 items-center px-4 justify-between border-b border-gray-100">
                        <div className="flex items-center gap-2">
                            {!sidebarOpen && (
                                <Button variant="ghost" size="icon"
                                    onClick={() => setSidebarOpen(true)}
                                    className="text-gray-600 hover:bg-gray-100"
                                    title="Open sidebar">
                                    <History className="h-5 w-5" />
                                </Button>
                            )}
                            <h1 className="text-xl font-medium">Assistant</h1>
                        </div>
                        <div className="flex items-center gap-1">
                            {user?.displayName && (
                                <span className="text-sm text-gray-500 mr-2">{user.displayName}</span>
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

                    {/* Chat + Research panels */}
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
                                key={chatKey}
                                className={hasInteracted ? "flex-1 min-h-0" : ""}
                                Input={CustomChatInput}
                                labels={{ initial: "" }}
                                onError={handleCopilotError}
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
    const [researchMode, setResearchMode] = useState(true);

    // Refresh token helper
    const refreshToken = useCallback(async (force = false) => {
        const t = await getIdToken(force);
        if (t) setToken(t);
        return t;
    }, [getIdToken]);

    // Initial token fetch + periodic refresh every 10 minutes
    useEffect(() => {
        if (user) {
            refreshToken();
            const interval = setInterval(() => refreshToken(true), 10 * 60 * 1000);
            return () => clearInterval(interval);
        } else {
            setToken(null);
        }
    }, [user, refreshToken]);

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
            properties={{ authorization: token, researchMode: researchMode }}
        >
            <ChatContent token={token} researchMode={researchMode} setResearchMode={setResearchMode} refreshToken={refreshToken} />
        </CopilotKit>
    );
}
