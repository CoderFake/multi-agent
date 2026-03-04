'use client';

import { useCoAgentStateRender } from '@copilotkit/react-core';
import { CheckCircle, Circle, Loader2, XCircle } from 'lucide-react';

interface PlanTask {
    id: string;
    name: string;
    toolName: string;
    status: 'pending' | 'running' | 'completed' | 'error';
}

/**
 * Renders the live execution plan status inside CopilotChat.
 * Shows only task name + simple status icon. Hidden when plan is empty
 * or all-pending (HITLApproval handles that phase instead).
 */
export function ExecutionPlanDisplay() {
    useCoAgentStateRender({
        name: 'default',
        render: ({ state }) => {
            const tasks = state?.execution_plan as PlanTask[] | undefined;
            if (!tasks || tasks.length === 0) return null;
            // While all pending → HITLApproval card is showing; skip duplicate
            if (tasks.every(t => t.status === 'pending')) return null;

            const getIcon = (status: PlanTask['status']) => {
                switch (status) {
                    case 'completed': return <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />;
                    case 'running':   return <Loader2 className="h-4 w-4 text-blue-500 animate-spin flex-shrink-0" />;
                    case 'error':     return <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />;
                    default:          return <Circle className="h-4 w-4 text-gray-400 flex-shrink-0" />;
                }
            };

            return (
                <div className="border rounded-xl bg-card p-3 my-1 space-y-1.5 animate-in slide-in-from-top duration-300">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Execution Plan</p>
                    {tasks.map((task, i) => (
                        <div key={task.id} className="flex items-center gap-2 text-sm text-gray-800">
                            {getIcon(task.status)}
                            <span className="text-muted-foreground mr-0.5">{i + 1}.</span>
                            {task.name}
                        </div>
                    ))}
                </div>
            );
        },
    });

    return null;
}
