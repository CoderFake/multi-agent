"use client";

import { useEffect, useRef, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { useAuth } from "@/lib/auth-client";

interface CopilotKitProviderProps {
  children: React.ReactNode;
}

/**
 * CopilotKit provider that injects the x-user-id header.
 *
 * Uses client-side useSession() hook to reactively get the user ID,
 * ensuring the header is set correctly after login without requiring
 * a full page reload.
 *
 * This header is forwarded by CopilotKit to the ADK backend,
 * where user_id_extractor reads it to create per-user sessions.
 */
export function CopilotKitProvider({ children }: CopilotKitProviderProps) {
  const { data: session, isPending } = useAuth();
  const userId = session?.user?.id ?? session?.user?.email ?? undefined;
  const [enabledAgents, setEnabledAgents] = useState<string>("");
  const prevUserIdRef = useRef<string | undefined>(undefined);
  const mountTimeRef = useRef<number>(Date.now());

  // Subscribe to agent config changes
  useEffect(() => {
    const loadAgentConfig = async () => {
      let saved = localStorage.getItem("enabled_agents");

      if (!saved) {
        try {
          const res = await fetch("/api/agents");
          if (res.ok) {
            const data = await res.json();
            const defaults: Record<string, boolean> = {};
            data.forEach((a: any) => (defaults[a.id] = true));
            saved = JSON.stringify(defaults);
            localStorage.setItem("enabled_agents", saved);
          }
        } catch (e) {
          console.error("Failed to fetch default agents", e);
        }
      }

      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          const activeIds = Object.entries(parsed)
            .filter(([_, isActive]) => isActive)
            .map(([id]) => id)
            .join(",");
          setEnabledAgents(activeIds);
        } catch (e) {
          console.error("Failed to parse agent settings", e);
        }
      }
    };

    loadAgentConfig();
    window.addEventListener("agent-config-changed", loadAgentConfig);
    return () => window.removeEventListener("agent-config-changed", loadAgentConfig);
  }, []);

  // Log auth state transitions for debugging
  useEffect(() => {
    const elapsed = Date.now() - mountTimeRef.current;

    if (isPending) {
      console.log("[CopilotKit:auth] session loading...", { elapsed: `${elapsed}ms` });
      return;
    }

    prevUserIdRef.current = userId;
  }, [userId, isPending]);

  useEffect(() => {
    if (userId && prevUserIdRef.current === undefined) {
      console.log("[CopilotKit:auth] headers now configured:", {
        "x-user-id": userId,
        "x-enabled-agents": enabledAgents,
        note: "If requests still fail, ensure CopilotKit re-initialises on header changes",
      });
    }
  }, [userId]);

  const headers = {
    ...(userId ? { "x-user-id": userId } : {}),
    "x-enabled-agents": enabledAgents
  };
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="root_agent"
      publicLicenseKey={process.env.NEXT_PUBLIC_COPILOTKIT_PUBLIC_KEY}
      headers={headers}
    >
      {children}
    </CopilotKit>
  );
}
