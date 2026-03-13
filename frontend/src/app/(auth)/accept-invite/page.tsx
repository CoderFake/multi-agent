"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { confirmInvite } from "@/lib/auth";
import type { ApiError } from "@/lib/api-client";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function AcceptInvitePage() {
    const ta = useTranslations("auth");
    const te = useTranslations("errors");
    const router = useRouter();
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [email, setEmail] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const hasConfirmed = useRef(false);

    useEffect(() => {
        if (hasConfirmed.current) return;
        hasConfirmed.current = true;

        const hash = window.location.hash;
        let token = "";

        if (hash.startsWith("#token=")) {
            token = hash.substring(7);
        } else if (hash.startsWith("#")) {
            token = hash.substring(1);
        }

        if (!token) {
            setStatus("error");
            setErrorMessage(ta("missingToken"));
            return;
        }

        const doConfirm = async () => {
            try {
                const response = await confirmInvite(token);
                setEmail(response.email);
                setStatus("success");
                setTimeout(() => router.push("/login"), 3000);
            } catch (err: unknown) {
                setStatus("error");
                const apiErr = err as ApiError;
                const errorKey = apiErr.error_code || "UNKNOWN_ERROR";
                setErrorMessage(te(errorKey));
            }
        };

        doConfirm();
    }, [router, ta, te]);

    return (
        <>
            <Card className="border-border/50 shadow-xl">
                <CardHeader className="text-center space-y-2">
                    <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                        {status === "loading" && <Loader2 className="h-6 w-6 text-primary animate-spin" />}
                        {status === "success" && <CheckCircle className="h-6 w-6 text-green-600" />}
                        {status === "error" && <XCircle className="h-6 w-6 text-destructive" />}
                    </div>
                    <CardTitle className="text-2xl font-bold">
                        {status === "loading" && ta("processingInvite")}
                        {status === "success" && ta("inviteAccepted")}
                        {status === "error" && ta("inviteError")}
                    </CardTitle>
                    <CardDescription>
                        {status === "loading" && ta("processingInviteDesc")}
                        {status === "success" && ta("inviteAcceptedDesc")}
                        {status === "error" && errorMessage}
                    </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4">
                    {status === "success" && (
                        <>
                            <div className="rounded-lg border bg-muted/50 p-4 text-center">
                                <p className="text-sm text-muted-foreground mb-1">{ta("yourEmail")}</p>
                                <p className="text-lg font-semibold">{email}</p>
                            </div>
                            <p className="text-sm text-muted-foreground text-center">
                                {ta("redirectingLogin")}
                            </p>
                            <Button className="w-full" onClick={() => router.push("/login")}>
                                {ta("goToLogin")}
                            </Button>
                        </>
                    )}

                    {status === "error" && (
                        <Button variant="outline" className="w-full" onClick={() => router.push("/login")}>
                            {ta("backToLogin")}
                        </Button>
                    )}
                </CardContent>
            </Card>
        </>
    );
}
