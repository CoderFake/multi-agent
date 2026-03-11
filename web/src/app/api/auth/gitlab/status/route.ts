import { NextResponse } from "next/server";
import { eq, and } from "drizzle-orm";
import { getAuthenticatedUser } from "@/lib/auth";
import { createPostgresDb } from "@/lib/db";
import { oauthConnections } from "@/lib/schema";

const GITLAB_PROVIDER = "gitlab";

export async function GET() {
    const user = await getAuthenticatedUser();

    if (!user?.uid) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const db = createPostgresDb();

        // Find connection for this user
        const connections = await db
            .select({
                providerEmail: oauthConnections.providerEmail,
                scopes: oauthConnections.scopes,
            })
            .from(oauthConnections)
            .where(
                and(
                    eq(oauthConnections.userId, user.uid),
                    eq(oauthConnections.provider, GITLAB_PROVIDER),
                ),
            )
            .limit(1);

        if (connections.length === 0) {
            return NextResponse.json({
                connected: false,
            });
        }

        const connection = connections[0];

        return NextResponse.json({
            connected: true,
            email: connection.providerEmail,
            url: connection.scopes,
        });
    } catch (err) {
        console.error("GitLab status check error:", err);
        return NextResponse.json({ error: "Failed to check connection status" }, { status: 500 });
    }
}
