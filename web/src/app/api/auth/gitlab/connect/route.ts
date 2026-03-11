import { NextResponse } from "next/server";
import { eq, and } from "drizzle-orm";
import { getAuthenticatedUser } from "@/lib/auth";
import { createPostgresDb } from "@/lib/db";
import { oauthConnections, user as userTable } from "@/lib/schema";

const GITLAB_PROVIDER = "gitlab";

export async function POST(request: Request) {
    const authUser = await getAuthenticatedUser();

    if (!authUser?.uid) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const body = await request.json();
        const { url, username, pat } = body;

        if (!url || !username || !pat) {
            return NextResponse.json({ error: "Missing required fields: url, username, pat" }, { status: 400 });
        }

        const db = createPostgresDb();

        await db
            .insert(userTable)
            .values({
                id: authUser.uid,
                name: authUser.name ?? authUser.email ?? authUser.uid,
                email: authUser.email ?? `${authUser.uid}@unknown`,
                emailVerified: authUser.email_verified ?? false,
            })
            .onConflictDoUpdate({
                target: userTable.id,
                set: {
                    email: authUser.email ?? `${authUser.uid}@unknown`,
                    name: authUser.name ?? authUser.email ?? authUser.uid,
                    updatedAt: new Date(),
                },
            });

        // Check if a GitLab connection already exists
        const existing = await db
            .select()
            .from(oauthConnections)
            .where(
                and(
                    eq(oauthConnections.userId, authUser.uid),
                    eq(oauthConnections.provider, GITLAB_PROVIDER),
                ),
            )
            .limit(1);

        if (existing.length > 0) {
            await db
                .update(oauthConnections)
                .set({
                    accessToken: pat,
                    providerEmail: username,
                    scopes: url,
                    updatedAt: new Date(),
                })
                .where(
                    and(
                        eq(oauthConnections.userId, authUser.uid),
                        eq(oauthConnections.provider, GITLAB_PROVIDER),
                    ),
                );
        } else {
            await db.insert(oauthConnections).values({
                id: crypto.randomUUID(),
                userId: authUser.uid,
                provider: GITLAB_PROVIDER,
                accessToken: pat,
                providerEmail: username,
                scopes: url,
            });
        }

        return NextResponse.json({ success: true });
    } catch (err) {
        console.error("GitLab connect error:", err);
        return NextResponse.json({ error: "Failed to save GitLab connection" }, { status: 500 });
    }
}
