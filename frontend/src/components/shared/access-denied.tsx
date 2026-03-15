"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AccessDeniedProps {
    /** The permission codename that was denied */
    permission?: string;
}

/**
 * Full-page 403 Forbidden UI shown when a user tries to access a page
 * they don't have permission for.
 */
export function AccessDenied({ permission }: AccessDeniedProps) {
    const t = useTranslations("common");
    const router = useRouter();

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-4">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
                <ShieldX className="h-10 w-10 text-destructive" />
            </div>
            <div className="space-y-2">
                <h2 className="text-2xl font-bold tracking-tight">
                    {t("accessDeniedTitle")}
                </h2>
                <p className="text-muted-foreground max-w-md">
                    {t("accessDeniedDesc")}
                </p>
                {permission && (
                    <p className="text-xs text-muted-foreground/60 font-mono mt-2">
                        {t("requiredPermission")}: {permission}
                    </p>
                )}
            </div>
            <Button variant="outline" onClick={() => router.back()} className="mt-2">
                {t("goBack")}
            </Button>
        </div>
    );
}
