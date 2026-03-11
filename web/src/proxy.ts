import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Proxy for route protection (Next.js 16+).
 *
 * Uses the __session cookie (Firebase ID token) to determine auth state.
 * - Unauthenticated users → /login
 * - Authenticated users → full app access
 *
 * Note: Full token verification happens in API routes via Firebase Admin SDK.
 * The proxy only checks for cookie presence (fast path).
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes that don't require authentication
  const isPublicRoute =
    pathname.startsWith("/api/auth") || pathname.startsWith("/privacy");
  if (isPublicRoute) {
    return NextResponse.next();
  }

  // Check for session cookie (Firebase ID token)
  const sessionCookie = request.cookies.get("__session")?.value;

  // Auth routes for unauthenticated users
  const isUnauthenticatedRoute =
    pathname.startsWith("/login") || pathname.startsWith("/register");

  // No session - must login (unless already on login/register)
  if (!sessionCookie) {
    if (isUnauthenticatedRoute) {
      return NextResponse.next();
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Has session, trying to access auth routes - redirect to app
  if (isUnauthenticatedRoute) {
    return NextResponse.redirect(new URL("/chat/new", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Match all routes except static files and specific API routes
  matcher: [
    "/((?!_next/static|_next/image|icon|apple-icon|favicon.ico|api/copilotkit|api/sessions|api/events|api/health).*)",
  ],
};
