import { NextResponse } from "next/server";
import { getAuthenticatedUser } from "@/lib/auth";

const agentUrl = process.env.AGENT_URL;

if (!agentUrl) {
  throw new Error(
    "AGENT_URL environment variable is required. Set it in web/.env.development or your deployment environment.",
  );
}

interface RouteParams {
  params: Promise<{ sessionId: string }>;
}

/**
 * POST /api/sessions/[sessionId]/cancel
 * Proxies to backend to cancel an active agent execution.
 * Requires authentication.
 */
export async function POST(_request: Request, { params }: RouteParams) {
  const { sessionId } = await params;

  const user = await getAuthenticatedUser();
  const userId = user?.id ?? user?.email;

  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const response = await fetch(
    `${agentUrl}/api/sessions/${encodeURIComponent(sessionId)}/cancel`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
