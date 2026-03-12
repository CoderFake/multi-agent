import { NextResponse, type NextRequest } from "next/server";

/**
 * Next.js middleware: redirect unauthenticated users to /login.
 * We check the presence of access_token cookie (no JWT verification here —
 * the backend verifies tokens).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public paths — no auth needed
  const publicPaths = ["/login", "/accept-invite", "/forgot-password"];
  const isPublic = publicPaths.some((p) => pathname.startsWith(p));

  const hasToken = request.cookies.has("access_token");

  // Redirect authenticated users away from auth pages
  if (isPublic && hasToken) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Redirect unauthenticated users to login
  if (!isPublic && !hasToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all paths except api routes, static files, and Next.js internals
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
