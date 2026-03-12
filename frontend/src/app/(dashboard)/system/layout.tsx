"use client";

import { useCurrentOrg } from "@/contexts/org-context";
import { useAuth } from "@/contexts/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SystemLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isSuperuser } = useCurrentOrg();
  const { isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isSuperuser) {
      router.push("/dashboard");
    }
  }, [isLoading, isSuperuser, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isSuperuser) return null;

  return <>{children}</>;
}
