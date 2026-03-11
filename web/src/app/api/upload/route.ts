import { NextRequest, NextResponse } from "next/server";
import { getAuthenticatedUser } from "@/lib/auth";

const agentUrl = process.env.AGENT_URL;

if (!agentUrl) {
  throw new Error(
    "AGENT_URL environment variable is required. Set it in web/.env.development or your deployment environment.",
  );
}

// Cache config for 5 minutes (not sensitive, rarely changes)
let configCache: { data: unknown; expiry: number } | null = null;
const CONFIG_TTL_MS = 5 * 60 * 1000;

/**
 * GET /api/upload
 * Returns upload config (supported types, size limits) from backend.
 * Cached to avoid repeated calls.
 */
export async function GET() {
  const now = Date.now();

  if (configCache && now < configCache.expiry) {
    return NextResponse.json(configCache.data);
  }

  const response = await fetch(`${agentUrl}/api/upload/config`);
  const data = await response.json();

  if (response.ok) {
    configCache = { data, expiry: now + CONFIG_TTL_MS };
  }

  return NextResponse.json(data, { status: response.status });
}

/**
 * POST /api/upload
 * Proxies file uploads to the ADK backend's /upload endpoint.
 *
 * Expects:
 * - FormData with 'file' field
 * - x-session-id header (threadId from CopilotKit)
 *
 * User ID is extracted from Firebase session for security.
 */
export async function POST(request: NextRequest) {
  const user = await getAuthenticatedUser();
  const userId = user?.uid ?? user?.email;

  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const sessionId = request.headers.get("x-session-id");

  if (!sessionId) {
    return NextResponse.json({ error: "Missing x-session-id header" }, { status: 400 });
  }

  // Forward the FormData to the backend
  const formData = await request.formData();

  const response = await fetch(`${agentUrl}/upload`, {
    method: "POST",
    headers: {
      "x-session-id": sessionId,
      "x-user-id": userId,
    },
    body: formData,
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
