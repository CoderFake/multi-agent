import { NextRequest, NextResponse } from "next/server";

export const GET = async (req: NextRequest) => {
    const agentUrl = process.env.AGENT_URL;

    if (!agentUrl) {
        return NextResponse.json(
            { error: "AGENT_URL environment variable is required" },
            { status: 500 }
        );
    }

    try {
        const response = await fetch(`${agentUrl}/agents`, {
            headers: {
                "Content-Type": "application/json",
            },
            next: { revalidate: 60 } // Cache for 60 seconds
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch agents: ${response.statusText}`);
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Error fetching agents API:", error);
        return NextResponse.json(
            { error: "Failed to fetch agents list" },
            { status: 500 }
        );
    }
};
