// frontend/lib/copilotkit-events.ts

import { useState, useEffect } from 'react';

export interface ThinkingStepEvent {
    type: 'analysis' | 'planning' | 'validation' | 'execution';
    message: string;
    status: 'active' | 'completed' | 'error';
}

export interface PlanTaskEvent {
    id: string;
    name: string;
    toolName?: string;
    args?: any;
    status: 'pending' | 'running' | 'completed' | 'error';
}

export interface CopilotKitStateEvent {
    thinking_step?: ThinkingStepEvent;
    execution_plan?: PlanTaskEvent[];
    plan_task_update?: {
        id: string;
        status: 'pending' | 'running' | 'completed' | 'error';
    };
    artifact_display?: {
        content: string;
        contentType: 'code' | 'html';
        fileName?: string;
        language?: string;
    };
}

export function emitCopilotKitState(state: CopilotKitStateEvent) {
    const event = new CustomEvent('copilotkit:state', {
        detail: state
    });
    window.dispatchEvent(event);
}

export function subscribeToCopilotKitState(
    callback: (state: CopilotKitStateEvent) => void
): () => void {
    const handler = (event: Event) => {
        const customEvent = event as CustomEvent<CopilotKitStateEvent>;
        callback(customEvent.detail);
    };

    window.addEventListener('copilotkit:state', handler);

    return () => {
        window.removeEventListener('copilotkit:state', handler);
    };
}


export function useCopilotKitState() {
    const [thinkingSteps, setThinkingSteps] = useState<ThinkingStepEvent[]>([]);
    const [executionPlan, setExecutionPlan] = useState<PlanTaskEvent[]>([]);
    const [isThinking, setIsThinking] = useState(false);

    useEffect(() => {
        const unsubscribe = subscribeToCopilotKitState((state) => {
            if (state.thinking_step) {
                setIsThinking(state.thinking_step.status === 'active');

                setThinkingSteps(prev => {
                    const existing = prev.find(s =>
                        s.message === state.thinking_step!.message &&
                        s.type === state.thinking_step!.type
                    );

                    if (existing) {
                        return prev.map(s =>
                            s.message === state.thinking_step!.message &&
                                s.type === state.thinking_step!.type
                                ? { ...s, status: state.thinking_step!.status }
                                : s
                        );
                    }

                    return [...prev, state.thinking_step!];
                });
            }

            if (state.execution_plan) {
                setExecutionPlan(state.execution_plan);
            }

            if (state.plan_task_update) {
                setExecutionPlan(prev =>
                    prev.map(task =>
                        task.id === state.plan_task_update!.id
                            ? { ...task, status: state.plan_task_update!.status }
                            : task
                    )
                );
            }
        });

        return unsubscribe;
    }, []);

    useEffect(() => {
        const allCompleted =
            thinkingSteps.length > 0 &&
            thinkingSteps.every(s => s.status === 'completed') &&
            executionPlan.length > 0 &&
            executionPlan.every(t => t.status === 'completed' || t.status === 'error');

        if (allCompleted) {
            setTimeout(() => {
                setIsThinking(false);
                setTimeout(() => {
                    setThinkingSteps([]);
                    setExecutionPlan([]);
                }, 3000);
            }, 1000);
        }
    }, [thinkingSteps, executionPlan]);

    return {
        thinkingSteps,
        executionPlan,
        isThinking
    };
}