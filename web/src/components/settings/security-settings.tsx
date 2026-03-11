"use client";

import { useAuth, signOut } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

/**
 * Security settings — simplified for Firebase Auth.
 * Firebase manages sessions and MFA natively via the Firebase Console.
 */
export function SecuritySettings() {
  const { data: session } = useAuth();
  const router = useRouter();
  const user = session?.user;

  if (!user) return null;

  const handleSignOut = async () => {
    await signOut();
    toast.success("Signed out successfully");
    router.push("/login");
  };

  return (
    <div className="space-y-0">
      {/* Account info */}
      <div className="flex items-center justify-between gap-4 py-4">
        <div>
          <p className="text-sm font-medium">Signed in as</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{user.email}</p>
        </div>
      </div>

      <div className="border-b border-border/50" />

      {/* Sign out */}
      <div className="flex items-center justify-between gap-4 py-4">
        <div>
          <p className="text-sm font-medium">Sign out</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Sign out of your account on this device
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleSignOut}>
          Sign out
        </Button>
      </div>
    </div>
  );
}
