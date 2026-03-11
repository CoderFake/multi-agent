"use client";

import { useEffect, useState } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface AgentConfig {
    id: string;
    name: string;
    description: string;
}

export function AgentsSettings() {
    const [agentsList, setAgentsList] = useState<AgentConfig[]>([]);
    const [enabledAgents, setEnabledAgents] = useState<Record<string, boolean>>({});
    const [isLoaded, setIsLoaded] = useState(false);
    const [isLoadingAgents, setIsLoadingAgents] = useState(true);

    useEffect(() => {
        // Fetch available agents from backend
        const fetchAgents = async () => {
            try {
                const response = await fetch("/api/agents");
                if (response.ok) {
                    const data: AgentConfig[] = await response.json();
                    setAgentsList(data);

                    // Load config from localStorage
                    const saved = localStorage.getItem("enabled_agents");
                    let initialConfig: Record<string, boolean> = {};

                    if (saved) {
                        initialConfig = JSON.parse(saved);
                    } else {
                        // By default, enable all fetched agents initially
                        data.forEach((a: AgentConfig) => {
                            initialConfig[a.id] = true;
                        });
                        localStorage.setItem("enabled_agents", JSON.stringify(initialConfig));
                    }

                    setEnabledAgents(initialConfig);
                    setIsLoaded(true);
                }
            } catch (e) {
                console.error("Failed to load agents", e);
            } finally {
                setIsLoadingAgents(false);
            }
        };

        fetchAgents();
    }, []);

    const handleToggle = (id: string, checked: boolean) => {
        const newConfig = { ...enabledAgents, [id]: checked };
        setEnabledAgents(newConfig);
        localStorage.setItem("enabled_agents", JSON.stringify(newConfig));

        // Dispatch a custom event so CopilotKitProvider can react to changes
        window.dispatchEvent(new Event("agent-config-changed"));
    };

    if (!isLoaded && !isLoadingAgents) {
        return null;
    }

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-base font-medium">Sub-Agents</h3>
                <p className="text-sm text-muted-foreground">
                    Enable or disable specific skills for your main assistant.
                </p>
            </div>

            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2 pb-2">
                {isLoadingAgents ? (
                    <p className="text-sm text-muted-foreground animate-pulse">Loading agents configuration...</p>
                ) : agentsList.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No agents found.</p>
                ) : (
                    agentsList.map((agent) => (
                        <div
                            key={agent.id}
                            className="flex items-center justify-between rounded-lg border border-border p-4 bg-card"
                        >
                            <div className="space-y-0.5 pr-4">
                                <Label className="text-base">{agent.name}</Label>
                                <p className="text-sm text-muted-foreground">{agent.description}</p>
                            </div>
                            <Switch
                                checked={!!enabledAgents[agent.id]}
                                onCheckedChange={(checked) => handleToggle(agent.id, checked)}
                            />
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
