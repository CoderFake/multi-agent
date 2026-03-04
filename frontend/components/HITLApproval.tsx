'use client';

import { useCoAgentStateRender } from '@copilotkit/react-core';
import { useCopilotChat } from '@copilotkit/react-core';
import { TextMessage, MessageRole } from '@copilotkit/runtime-client-gql';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface PlanTask {
    id: string;
    name: string;
    toolName: string;
    status: 'pending' | 'running' | 'completed' | 'error';
}

/**
 * Renders HITL approval card inside CopilotChat whenever execution_plan
 * is ready (status = "pending") and awaiting user decision.
 * Sends "approved" / "rejected" text to resume the LangGraph interrupt().
 */
export function HITLApproval() {
    const { appendMessage, isLoading } = useCopilotChat();

    const respond = async (decision: 'approved' | 'rejected') => {
        await appendMessage(
            new TextMessage({ role: MessageRole.User, content: decision })
        );
    };

    useCoAgentStateRender({
        name: 'default',
        render: ({ state }) => {
            const plan = state?.execution_plan as PlanTask[] | undefined;

            // Only show when plan exists and all tasks are still pending (awaiting approval)
            if (!plan || plan.length === 0) return null;
            if (!plan.every(t => t.status === 'pending')) return null;

            return (
                <div className="border border-indigo-200 rounded-xl bg-indigo-50/60 p-4 my-1 space-y-3 animate-in slide-in-from-top duration-300">
                    <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />
                        <p className="text-sm font-semibold text-indigo-800">Agent needs your approval</p>
                    </div>

                    {/* Task list — name only */}
                    <ul className="space-y-1 pl-1">
                        {plan.map((task, i) => (
                            <li key={task.id} className="flex items-center gap-2 text-sm text-gray-700">
                                <span className="w-5 h-5 flex items-center justify-center rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold flex-shrink-0">
                                    {i + 1}
                                </span>
                                {task.name}
                            </li>
                        ))}
                    </ul>

                    {/* Approve / Reject buttons */}
                    <div className="flex gap-2 pt-1">
                        <button
                            disabled={isLoading}
                            onClick={() => respond('approved')}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
                        >
                            <CheckCircle className="h-4 w-4" />
                            Approve
                        </button>
                        <button
                            disabled={isLoading}
                            onClick={() => respond('rejected')}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white hover:bg-red-50 border border-red-300 text-red-600 text-sm font-medium disabled:opacity-50 transition-colors"
                        >
                            <XCircle className="h-4 w-4" />
                            Reject
                        </button>
                    </div>
                </div>
            );
        },
    });

    return null;
}
