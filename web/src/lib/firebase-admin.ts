/**
 * Firebase Admin SDK configuration (server-side only).
 *
 * Used to verify Firebase ID tokens in API routes and proxy.
 * Credentials come from environment variables (service account).
 */

import { initializeApp, getApps, cert, type App } from "firebase-admin/app";
import { getAuth, type Auth } from "firebase-admin/auth";

function getAdminApp(): App {
  if (getApps().length > 0) {
    return getApps()[0];
  }

  // Build service account from individual env vars
  const projectId = process.env.FIREBASE_PROJECT_ID;
  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n");

  if (!projectId || !clientEmail || !privateKey) {
    throw new Error(
      "Firebase Admin SDK credentials not configured. " +
        "Set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY.",
    );
  }

  return initializeApp({
    credential: cert({ projectId, clientEmail, privateKey }),
  });
}

const adminApp = getAdminApp();
export const adminAuth: Auth = getAuth(adminApp);

/**
 * Verify a Firebase ID token and return the decoded claims.
 * Returns null if the token is invalid or expired.
 */
export async function verifyIdToken(idToken: string) {
  try {
    return await adminAuth.verifyIdToken(idToken);
  } catch {
    return null;
  }
}

/**
 * Extract Firebase ID token from request cookies or Authorization header.
 * Cookie name: __session (Firebase convention for hosting)
 */
export function extractToken(request: Request): string | null {
  // Try Authorization header first
  const authHeader = request.headers.get("Authorization");
  if (authHeader?.startsWith("Bearer ")) {
    return authHeader.slice(7);
  }

  // Try cookie
  const cookies = request.headers.get("cookie");
  if (cookies) {
    const match = cookies.match(/(?:^|;\s*)__session=([^;]*)/);
    if (match) {
      return match[1];
    }
  }

  return null;
}

/**
 * Get authenticated user email from a request.
 * Combines token extraction and verification.
 * Returns null if not authenticated.
 */
export async function getAuthenticatedEmail(request: Request): Promise<string | null> {
  const token = extractToken(request);
  if (!token) return null;

  const decoded = await verifyIdToken(token);
  return decoded?.email ?? null;
}

