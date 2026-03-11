/**
 * Server-side auth utilities using Firebase Admin SDK.
 *
 * Provides helpers to get the authenticated user from
 * the __session cookie (set by /api/auth/session).
 */

import { cookies } from "next/headers";
import { verifyIdToken } from "./firebase-admin";

/**
 * Get the authenticated user's email from the session cookie.
 * Used in API routes and server components.
 * Returns null if not authenticated.
 */
export async function getAuthenticatedEmail(): Promise<string | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("__session")?.value;
  if (!token) return null;

  const decoded = await verifyIdToken(token);
  return decoded?.email ?? null;
}

/**
 * Get the full decoded Firebase token from the session cookie.
 * Returns null if not authenticated.
 */
export async function getAuthenticatedUser() {
  const cookieStore = await cookies();
  const token = cookieStore.get("__session")?.value;
  if (!token) return null;

  return verifyIdToken(token);
}
