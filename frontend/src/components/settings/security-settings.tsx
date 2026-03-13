"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";

export function SecuritySettings() {
    const t = useTranslations("settings");
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (newPassword.length < 8) {
            setError(t("passwordMinLength"));
            return;
        }
        if (newPassword !== confirmPassword) {
            setError(t("passwordMismatch"));
            return;
        }

        setLoading(true);
        try {
            // TODO: call API to change password
            await new Promise((r) => setTimeout(r, 500));
            setSuccess(true);
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
            setTimeout(() => setSuccess(false), 3000);
        } catch {
            setError(t("passwordChangeFailed"));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-sm font-medium">{t("changePassword")}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{t("changePasswordDesc")}</p>
            </div>

            <form onSubmit={handleSubmit} className="max-w-sm space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">{t("currentPassword")}</label>
                    <Input
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        required
                        placeholder={t("enterCurrentPassword")}
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium">{t("newPassword")}</label>
                    <Input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        minLength={8}
                        placeholder={t("atLeast8Chars")}
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium">{t("confirmNewPassword")}</label>
                    <Input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        placeholder={t("confirmNewPasswordPlaceholder")}
                    />
                </div>

                {error && <p className="text-sm text-destructive">{error}</p>}
                {success && <p className="text-sm text-green-500">{t("passwordChanged")}</p>}

                <Button type="submit" disabled={loading}>
                    {loading && <Loader2 className="mr-2 size-4 animate-spin" />}
                    {t("updatePassword")}
                </Button>
            </form>
        </div>
    );
}
