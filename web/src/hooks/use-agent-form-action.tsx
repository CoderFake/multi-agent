"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { useEffect, useState, useMemo } from "react";
import { DynamicToolForm } from "@/components/forms/dynamic-tool-form";

/**
 * Generic CopilotKit action hook for rendering dynamic agent forms in chat.
 *
 * ## Architecture
 *
 * When the backend LLM calls `request_user_input(tool_name, project_id, form_defaults)`,
 * CopilotKit intercepts and invokes `renderAndWaitForResponse`.
 *
 * The hook then:
 * 1. Fetches the JSON Schema for the tool from `/api/agent-tools/schema`
 * 2. Fetches dropdown options from `/api/agent-tools/options` (which calls Redmine API)
 * 3. Renders a dynamic RJSF form with pre-filled values and populated dropdowns
 * 4. Waits for user submission, then returns formData to the LLM
 *
 * Usage: Call once in a top-level component wrapping the chat.
 *   useAgentFormAction();
 */
/**
 * Internal wrapper component to isolate React hooks from CopilotKit's render callback,
 * fixing "Rules of Hooks" execution order errors.
 */
function AgentFormWrapper({ args, respond, status, result }: any) {
    const [baseSchema, setBaseSchema] = useState<object | null>(null);
    const [fetchedOptions, setFetchedOptions] = useState<Record<string, { enum: (number | string)[]; enumNames: string[] }>>({});
    const [error, setError] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState<Record<string, unknown> | null>(null);
    const [currentContext, setCurrentContext] = useState<Record<string, unknown>>(() => (args.form_defaults as Record<string, unknown>) || {});

    // Fetch JSON Schema (Runs ONCE on mount)
    useEffect(() => {
        if (!args.tool_name) return;
        const agentParam = args.agent ? `&agent=${args.agent}` : "";

        fetch(`/api/agent-tools/schema?tool=${args.tool_name}${agentParam}`)
            .then((r) => {
                if (!r.ok) throw new Error(`Schema not found for tool: ${args.tool_name}`);
                return r.json();
            })
            .then((schema) => setBaseSchema(schema))
            .catch((err: Error) => setError(err.message));
    }, [args.tool_name, args.agent]);

    // Extract dependent keys that should trigger option refetch
    const dependentKeys = useMemo(() => {
        const keys = new Set<string>();
        if (baseSchema && (baseSchema as any).properties) {
            for (const prop of Object.values((baseSchema as any).properties)) {
                const dependsOn = (prop as any).depends_on;
                if (dependsOn) {
                    if (Array.isArray(dependsOn)) dependsOn.forEach(k => keys.add(k));
                    else keys.add(dependsOn);
                }
            }
        }
        return Array.from(keys);
    }, [baseSchema]);

    // Calculate a stable string of just the dependent values
    const dependentContextString = useMemo(() => {
        const depContext: Record<string, unknown> = {};
        for (const key of dependentKeys) {
            depContext[key] = currentContext[key];
        }
        return JSON.stringify(depContext);
    }, [currentContext, dependentKeys]);

    // Fetch dropdown options (Runs on mount AND when dependent context changes)
    useEffect(() => {
        if (!args.tool_name) return;

        const timer = setTimeout(() => {
            const parsedContext = JSON.parse(dependentContextString);
            fetch(`/api/agent-tools/options`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tool: args.tool_name, agent: args.agent, context: parsedContext })
            })
                .then((r) => {
                    if (!r.ok) return {}; // Non-fatal
                    return r.json();
                })
                .then((options) => setFetchedOptions(options as Record<string, { enum: (number | string)[]; enumNames: string[] }>))
                .catch(() => ({})); // Non-fatal
        }, 400); // 400ms debounce to prevent API spam while typing

        return () => clearTimeout(timer);
    }, [args.tool_name, args.agent, dependentContextString]);

    // ── Completed state (form was submitted, session reloaded) ─────────
    if (status === "complete") {
        let parsedResult: Record<string, unknown> | null = null;
        if (result && typeof result === "string") {
            try { parsedResult = JSON.parse(result) as Record<string, unknown>; } catch { /* ignore */ }
        } else if (result && typeof result === "object") {
            parsedResult = result as Record<string, unknown>;
        }

        if (parsedResult?.cancelled) {
            return (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <span>✕</span>
                    <span>Form cancelled</span>
                </div>
            );
        }

        return (
            <div className="rounded-lg border border-border bg-muted/30 p-3 w-full my-1">
                <div className="flex items-center gap-2 text-sm font-medium text-green-600 mb-2">
                    <span>✓</span>
                    <span className="capitalize">{String(args.tool_name ?? "").replace(/_/g, " ")} — submitted</span>
                </div>
                {parsedResult && (
                    <dl className="text-xs grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-muted-foreground">
                        {Object.entries((parsedResult.data as Record<string, unknown>) || parsedResult)
                            .filter(([k, v]) => k !== "__system_instruction" && v !== null && v !== undefined && v !== "")
                            .map(([k, v]) => {
                                let displayValue = String(v);
                                const opt = fetchedOptions[k];
                                if (opt && opt.enum) {
                                    let idx = opt.enum.indexOf(v as string | number);
                                    if (idx === -1) {
                                        idx = opt.enum.findIndex(e => String(e) === String(v));
                                    }
                                    if (idx !== -1 && opt.enumNames?.[idx]) {
                                        displayValue = opt.enumNames[idx] as string;
                                    }
                                }
                                return (
                                    <div key={k} className="contents">
                                        <dt className="font-medium capitalize">{k.replace(/_/g, " ")}</dt>
                                        <dd>{displayValue}</dd>
                                    </div>
                                );
                            })}
                    </dl>
                )}
            </div>
        );
    }

    // ── In-progress: form is being submitted ──────────────────────────
    if (submitted) {
        return (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2 animate-pulse">
                <span className="h-3 w-3 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin" />
                <span>Submitting…</span>
            </div>
        );
    }

    // ── Error state ───────────────────────────────────────────────────
    if (error) {
        return (
            <div className="text-sm text-destructive py-2">
                ⚠ {error}
            </div>
        );
    }

    // ── Loading schema + options ──────────────────────────────────────
    if (!baseSchema) {
        return (
            <div className="text-sm text-muted-foreground py-2 animate-pulse">
                Loading form…
            </div>
        );
    }

    // ── Pre-process currentContext to match fetchedOptions ────────────
    const parsedContext = { ...currentContext };
    for (const [key, val] of Object.entries(parsedContext)) {
        if (val === "" || val === null || val === undefined) {
            delete parsedContext[key];
            continue;
        }

        if (fetchedOptions[key]?.enum?.length && typeof val === "string") {
            const isNumericEnum = fetchedOptions[key].enum.some(e => typeof e === "number");
            if (isNumericEnum && !isNaN(Number(val))) {
                parsedContext[key] = parseInt(val, 10);
            }
        }
    }

    // ── Active form ───────────────────────────────────────────────────
    return (
        <DynamicToolForm
            toolName={args.tool_name as string}
            baseSchema={baseSchema as Record<string, unknown>}
            options={fetchedOptions}
            formData={parsedContext}
            onChange={setCurrentContext}
            onSubmit={(formData: Record<string, unknown>) => {
                setSubmitted(formData);
                if (respond) respond(JSON.stringify({ accepted: true, data: formData }));
            }}
            onCancel={() => {
                if (respond) respond(JSON.stringify({ accepted: false }));
            }}
        />
    );
}

const AGENT_FORM_ACTION_CONFIG = {
    name: "request_user_input",
    description:
        "Render a dynamic form for the user to fill in required fields for any agent tool.",
    available: "remote" as const,
    parameters: [
        { name: "tool_name", type: "string" as const, required: true, description: "Tool name to render form for" },
        { name: "options", type: "object" as const, required: false, description: "Dynamic options (ignored — auto-fetched)" },
        { name: "project_id", type: "string" as const, required: false, description: "Project context for dropdown fetching" },
        { name: "agent", type: "string" as const, required: false, description: "Agent name for schema routing" },
        { name: "form_defaults", type: "object" as const, required: false, description: "Pre-fill values from LLM context" },
    ],
    renderAndWaitForResponse: ({ args, respond, status, result }: any) => {
        return (
            <AgentFormWrapper
                args={args}
                respond={respond}
                status={status}
                result={result}
            />
        );
    },
};

export function useAgentFormAction() {
    useCopilotAction(AGENT_FORM_ACTION_CONFIG);
}
