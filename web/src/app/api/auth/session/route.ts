import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { verifyIdToken } from "@/lib/firebase-admin";

/**
 * POST /api/auth/session
 * Sets the Firebase ID token as an httpOnly cookie (__session).
 * Called by the client after Firebase sign-in to sync auth state to the server.
 */
export async function POST(request: Request) {
  try {
    const { token } = await request.json();

    if (!token || typeof token !== "string") {
      return NextResponse.json({ error: "Token required" }, { status: 400 });
    }

    // Verify the token is valid before setting cookie
    const decoded = await verifyIdToken(token);
    if (!decoded) {
      return NextResponse.json({ error: "Invalid token" }, { status: 401 });
    }

    // Set httpOnly cookie (1 hour, matches Firebase token lifetime)
    const cookieStore = await cookies();
    cookieStore.set("__session", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60, // 1 hour
    });

    return NextResponse.json({ status: "ok" });
  } catch {
    return NextResponse.json({ error: "Failed to create session" }, { status: 500 });
  }
}

