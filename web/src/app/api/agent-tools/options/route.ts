import { NextResponse } from "next/server";
import { getAuthenticatedUser } from "@/lib/auth";

/**
 * POST /api/agent-tools/options
 * Body: { tool: "...", context: { project_id: "...", issue_id: "...", ... } }
 *
 * Proxy to backend POST /api/tools/{tool}/options
 * Passes the authenticated user's ID via X-User-Id header so the backend
 * can look up their Redmine/GitLab credentials and fetch dropdown data.
 */
export async function POST(request: Request) {
    const authUser = await getAuthenticatedUser();
    if (!authUser?.uid) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json().catch(() => ({}));
    const toolName = body.tool;
    const agent = body.agent;
    const context = body.context ?? {};

    if (!toolName) {
        return NextResponse.json({ error: "Missing 'tool' in request body" }, { status: 400 });
    }

    const backendUrl = process.env.AGENT_URL ?? "http://localhost:8000";

    try {
        const url = `${backendUrl}/api/tools/${toolName}/options?agent=${encodeURIComponent(agent || "")}`;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-User-Id": authUser.uid,
            },
            body: JSON.stringify(context),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            return NextResponse.json(
                { error: err.error ?? `Failed to fetch options for: ${toolName}` },
                { status: response.status }
            );
        }

        const options = await response.json();
        return NextResponse.json(options);
    } catch (err) {
        console.error("Failed to fetch agent tool options:", err);
        return NextResponse.json(
            { error: "Failed to fetch options from agent backend" },
            { status: 500 }
        );
    }
}
