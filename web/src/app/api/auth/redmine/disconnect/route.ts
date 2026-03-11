import { NextResponse } from "next/server";
import { eq, and } from "drizzle-orm";
import { getAuthenticatedUser } from "@/lib/auth";
import { createPostgresDb } from "@/lib/db";
import { oauthConnections } from "@/lib/schema";

const REDMINE_PROVIDER = "redmine";

export async function DELETE() {
    const user = await getAuthenticatedUser();

    if (!user?.uid) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const db = createPostgresDb();

        await db
            .delete(oauthConnections)
            .where(
                and(
                    eq(oauthConnections.userId, user.uid),
                    eq(oauthConnections.provider, REDMINE_PROVIDER),
                ),
            );

        return NextResponse.json({ success: true });
    } catch (err) {
        console.error("Redmine disconnect error:", err);
        return NextResponse.json({ error: "Failed to disconnect Redmine" }, { status: 500 });
    }
}
