import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// Use empty adapter since we're routing to a single ADK agent
const serviceAdapter = new ExperimentalEmptyAdapter();

// Backend agent URL - must be configured via AGENT_URL environment variable
const agentUrl = process.env.AGENT_URL;

if (!agentUrl) {
  throw new Error(
    "AGENT_URL environment variable is required. Set it in web/.env.development or your deployment environment.",
  );
}

// Track request count for correlation
let requestCount = 0;

// Next.js App Router API endpoint
export const POST = async (req: NextRequest) => {
  const requestId = ++requestCount;
  const userId = req.headers.get("x-user-id");
  const enabledAgents = req.headers.get("x-enabled-agents");

  const runtime = new CopilotRuntime({
    agents: {
      root_agent: new HttpAgent({
        url: agentUrl,
        headers: {
          ...(userId ? { "x-user-id": userId } : {}),
          ...(enabledAgents ? { "x-enabled-agents": enabledAgents } : {})
        }
      }),
    },
  })

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
