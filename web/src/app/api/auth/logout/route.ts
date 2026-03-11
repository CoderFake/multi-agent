import { NextResponse } from "next/server";
import { cookies } from "next/headers";

/**
 * POST /api/auth/logout
 * Clears the __session cookie.
 */
export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete("__session");
  return NextResponse.json({ status: "ok" });
}

