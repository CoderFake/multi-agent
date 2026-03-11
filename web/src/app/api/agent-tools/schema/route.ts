import { NextResponse } from "next/server";

/**
 * GET /api/agent-tools/schema?agent=redmine&tool=create_issue
 *
 * Generic proxy that fetches the Pydantic JSON Schema for any agent tool from
 * the backend. The backend must expose:
 *   GET /api/tools/{tool_name}/schema
 *
 * The `agent` param is reserved for future multi-agent schema routing.
 * Currently all tools are served from the same backend agent service.
 *
 * Adding a new agent's forms:
 *   1. Register it in backend SCHEMA_REGISTRY (schema/_registry.py)
 *   2. Call request_user_input(tool_name=..., options=...) from the backend agent
 *   3. Frontend useAgentFormAction automatically handles it via this endpoint
 */
export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const toolName = searchParams.get("tool");
    // agent param is for future use (routing to different backends)
    // const agent = searchParams.get("agent");

    if (!toolName) {
        return NextResponse.json({ error: "Missing 'tool' query parameter" }, { status: 400 });
    }

    const backendUrl = process.env.AGENT_URL ?? "http://localhost:8000";

    try {
        const response = await fetch(`${backendUrl}/api/tools/${toolName}/schema`, {
            headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) {
            return NextResponse.json(
                { error: `Schema not found for tool: ${toolName}` },
                { status: response.status }
            );
        }

        const schema = await response.json();
        return NextResponse.json(schema);
    } catch (err) {
        console.error("Failed to fetch agent tool schema:", err);
        return NextResponse.json(
            { error: "Failed to fetch schema from agent backend" },
            { status: 500 }
        );
    }
}
