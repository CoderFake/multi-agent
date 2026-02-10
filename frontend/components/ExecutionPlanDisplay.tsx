'use client';

import { useCoAgentStateRender } from '@copilotkit/react-core';
import { CheckCircle, Circle, Loader2, XCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface PlanTask {
    id: string;
    name: string;
    toolName: string;
    status: 'pending' | 'running' | 'completed' | 'error';
}

interface TaskUpdate {
    id: string;
    status: 'pending' | 'running' | 'completed' | 'error';
}

export function ExecutionPlanDisplay() {
    const [isCollapsed, setIsCollapsed] = useState(false);

    useCoAgentStateRender({
        name: 'default',
        render: ({ state }) => {
            // Get tasks directly from state
            const executionPlan = state?.execution_plan as PlanTask[] | undefined;

            // Handle task updates by merging with execution plan
            const taskUpdate = state?.plan_task_update as TaskUpdate | undefined;

            // Merge the execution plan with any task updates
            let tasks = executionPlan || [];
            if (taskUpdate && tasks.length > 0) {
                tasks = tasks.map(task =>
                    task.id === taskUpdate.id
                        ? { ...task, status: taskUpdate.status }
                        : task
                );
            }

            if (tasks.length === 0) {
                return null;
            }

            const getStatusIcon = (status: PlanTask['status']) => {
                switch (status) {
                    case 'completed':
                        return <CheckCircle className="h-4 w-4 text-green-500" />;
                    case 'running':
                        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
                    case 'error':
                        return <XCircle className="h-4 w-4 text-red-500" />;
                    default:
                        return <Circle className="h-4 w-4 text-gray-400" />;
                }
            };

            const getStatusBadge = (status: PlanTask['status']) => {
                const colors = {
                    pending: 'bg-gray-100 text-gray-600',
                    running: 'bg-blue-100 text-blue-700',
                    completed: 'bg-green-100 text-green-700',
                    error: 'bg-red-100 text-red-700'
                };

                return (
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status]}`}>
                        {status}
                    </span>
                );
            };

            const completedTasks = tasks.filter(t => t.status === 'completed').length;
            const progress = (completedTasks / tasks.length) * 100;

            return (
                <div className="border rounded-lg bg-card animate-in slide-in-from-top duration-300">
                    <div className="flex items-center justify-between p-3 border-b">
                        <div className="flex items-center gap-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setIsCollapsed(!isCollapsed)}
                                className="h-6 w-6 p-0"
                            >
                                {isCollapsed ? (
                                    <ChevronRight className="h-4 w-4" />
                                ) : (
                                    <ChevronDown className="h-4 w-4" />
                                )}
                            </Button>
                            <h3 className="font-semibold text-sm">Execution Plan</h3>
                            <span className="text-xs text-muted-foreground">
                                {completedTasks}/{tasks.length} tasks
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 transition-all duration-300"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                    </div>

                    {!isCollapsed && (
                        <div className="p-3 space-y-2">
                            {tasks.map((task, index) => (
                                <div
                                    key={task.id}
                                    className="flex items-center justify-between p-2 rounded-md hover:bg-muted/50 transition-colors"
                                >
                                    <div className="flex items-center gap-2">
                                        {getStatusIcon(task.status)}
                                        <span className="text-sm">
                                            <span className="text-muted-foreground mr-1">{index + 1}.</span>
                                            {task.name}
                                        </span>
                                    </div>
                                    {getStatusBadge(task.status)}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            );
        }
    });

    return null;
}
