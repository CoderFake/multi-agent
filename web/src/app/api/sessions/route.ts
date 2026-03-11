import { NextResponse } from "next/server";
import { getAuthenticatedUser } from "@/lib/auth";

const agentUrl = process.env.AGENT_URL;

if (!agentUrl) {
  throw new Error(
    "AGENT_URL environment variable is required. Set it in web/.env.development or your deployment environment.",
  );
}

/**
 * GET /api/sessions
 * Proxies to backend to list all chat sessions for the current user.
 * Requires authentication - user ID is extracted from Firebase session.
 */
export async function GET() {
  const user = await getAuthenticatedUser();
  const userId = user?.uid ?? user?.email;

  if (!userId) {
    return NextResponse.json({ error: "Unauthorized", sessions: [] }, { status: 401 });
  }

  const response = await fetch(`${agentUrl}/api/sessions?user_id=${encodeURIComponent(userId)}`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
