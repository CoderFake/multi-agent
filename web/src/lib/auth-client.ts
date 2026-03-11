/**
 * Firebase Auth client exports for React components.
 *
 * Provides:
 * - signIn / signUp / signOut functions
 * - useAuth hook for reactive auth state (replaces useSession)
 * - getIdToken helper for API calls
 */

"use client";

import { useState, useEffect } from "react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
  type User,
} from "firebase/auth";
import { firebaseAuth } from "./firebase";

// ── Sign In / Sign Up / Sign Out ──────────────────────────────────────

export async function signIn(email: string, password: string) {
  return signInWithEmailAndPassword(firebaseAuth, email, password);
}

export async function signInWithGoogle() {
  const provider = new GoogleAuthProvider();
  return signInWithPopup(firebaseAuth, provider);
}

export async function signUp(email: string, password: string) {
  return createUserWithEmailAndPassword(firebaseAuth, email, password);
}

export async function signOut() {
  // Clear the session cookie
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch {
    // Best-effort cookie cleanup
  }
  return firebaseSignOut(firebaseAuth);
}

// ── Get ID Token (for API calls / setting cookie) ─────────────────────

export async function getIdToken(): Promise<string | null> {
  const user = firebaseAuth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}

// ── Sync Firebase token → cookie ──────────────────────────────────────

async function syncSessionCookie(user: User | null) {
  if (user) {
    const token = await user.getIdToken();
    await fetch("/api/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
  }
}

// ── useAuth Hook (replaces Better Auth's useSession) ──────────────────

interface AuthState {
  user: User | null;
  isPending: boolean;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    isPending: true,
  });

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(firebaseAuth, async (user) => {
      await syncSessionCookie(user);
      setState({ user, isPending: false });
    });
    return unsubscribe;
  }, []);

  // Convenience: build a session-like object for compatibility
  const data = state.user
    ? {
      user: {
        id: state.user.uid,
        email: state.user.email,
        name: state.user.displayName,
        emailVerified: state.user.emailVerified,
      },
    }
    : null;

  return { data, isPending: state.isPending, user: state.user };
}

// ── Re-export for backward compat ─────────────────────────────────────
// Some components may still import useSession
export const useSession = useAuth;
