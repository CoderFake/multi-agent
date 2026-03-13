"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { changePassword } from "@/lib/auth";
import type { ApiError } from "@/lib/api-client";
import { Lock, Eye, EyeOff, Loader2 } from "lucide-react";

export default function ChangePasswordPage() {
    const ta = useTranslations("auth");
    const te = useTranslations("errors");
    const router = useRouter();
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmNewPassword, setConfirmNewPassword] = useState("");
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (newPassword.length < 8) {
            setError(ta("passwordMinLength"));
            return;
        }
        if (newPassword !== confirmNewPassword) {
            setError(ta("passwordMismatch"));
            return;
        }
        if (currentPassword === newPassword) {
            setError(ta("passwordSameAsCurrent"));
            return;
        }

        setLoading(true);
        try {
            await changePassword({
                current_password: currentPassword,
                new_password: newPassword,
            });
            router.push("/");
        } catch (err: unknown) {
            const apiErr = err as ApiError;
            const errorKey = apiErr.error_code || "CHANGE_PASSWORD_FAILED";
            setError(te(errorKey));
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <Card className="border-border/50 shadow-xl">
                <CardHeader className="text-center space-y-2">
                    <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                        <Lock className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-2xl font-bold">{ta("changePasswordTitle")}</CardTitle>
                    <CardDescription>{ta("changePasswordDesc")}</CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                                {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="current">{ta("currentPasswordLabel")}</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    id="current"
                                    type={showCurrent ? "text" : "password"}
                                    required
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    placeholder={ta("currentPasswordPlaceholder")}
                                    className="pl-10 pr-10"
                                    disabled={loading}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrent(!showCurrent)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="new">{ta("newPassword")}</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    id="new"
                                    type={showNew ? "text" : "password"}
                                    required
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    placeholder={ta("newPasswordPlaceholder")}
                                    className="pl-10 pr-10"
                                    disabled={loading}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNew(!showNew)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="confirm">{ta("confirmPassword")}</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    id="confirm"
                                    type="password"
                                    required
                                    value={confirmNewPassword}
                                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                                    placeholder={ta("confirmNewPasswordPlaceholder")}
                                    className="pl-10"
                                    disabled={loading}
                                />
                            </div>
                        </div>

                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {ta("changingPassword")}
                                </>
                            ) : (
                                ta("changePasswordButton")
                            )}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </>
    );
}
