"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { User, Mail, Shield, Save } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api-client";

export default function ProfilePage() {
    const t = useTranslations("profile");
    const { user } = useAuth();
    const [fullName, setFullName] = useState(user?.full_name || "");
    const [currentPwd, setCurrentPwd] = useState("");
    const [newPwd, setNewPwd] = useState("");
    const [confirmPwd, setConfirmPwd] = useState("");
    const [saving, setSaving] = useState(false);

    const handleUpdateProfile = useCallback(async () => {
        setSaving(true);
        try {
            await api.put("/auth/profile", { full_name: fullName });
            toast.success(t("profileUpdated"));
        } catch {
            toast.error(t("profileUpdateFailed"));
        } finally {
            setSaving(false);
        }
    }, [fullName, t]);

    const handleChangePassword = useCallback(async () => {
        if (newPwd !== confirmPwd) {
            toast.error(t("passwordMismatch"));
            return;
        }
        if (newPwd.length < 8) {
            toast.error(t("passwordTooShort"));
            return;
        }
        setSaving(true);
        try {
            await api.put("/auth/password", {
                current_password: currentPwd,
                new_password: newPwd,
            });
            toast.success(t("passwordChanged"));
            setCurrentPwd("");
            setNewPwd("");
            setConfirmPwd("");
        } catch {
            toast.error(t("passwordChangeFailed"));
        } finally {
            setSaving(false);
        }
    }, [currentPwd, newPwd, confirmPwd, t]);

    return (
        <div className="space-y-6 max-w-2xl">
            <PageHeader title={t("title")} description={t("description")} />

            {/* Profile Info */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                        <User className="h-4 w-4" />
                        {t("personalInfo")}
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <Label>{t("email")}</Label>
                        <Input value={user?.email || ""} disabled className="bg-muted" />
                    </div>
                    <div>
                        <Label>{t("fullName")}</Label>
                        <Input
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                        />
                    </div>
                    {user?.is_superuser && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Shield className="h-4 w-4 text-primary" />
                            {t("superuserBadge")}
                        </div>
                    )}
                    <Button onClick={handleUpdateProfile} disabled={saving} size="sm">
                        <Save className="h-4 w-4 mr-1" />
                        {saving ? t("saving") : t("saveChanges")}
                    </Button>
                </CardContent>
            </Card>

            {/* Change Password */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">{t("changePassword")}</CardTitle>
                    <CardDescription>{t("changePasswordDesc")}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <Label>{t("currentPassword")}</Label>
                        <Input
                            type="password"
                            value={currentPwd}
                            onChange={(e) => setCurrentPwd(e.target.value)}
                        />
                    </div>
                    <div>
                        <Label>{t("newPassword")}</Label>
                        <Input
                            type="password"
                            value={newPwd}
                            onChange={(e) => setNewPwd(e.target.value)}
                        />
                    </div>
                    <div>
                        <Label>{t("confirmPassword")}</Label>
                        <Input
                            type="password"
                            value={confirmPwd}
                            onChange={(e) => setConfirmPwd(e.target.value)}
                        />
                    </div>
                    <Button
                        onClick={handleChangePassword}
                        disabled={saving || !currentPwd || !newPwd}
                        size="sm"
                    >
                        {saving ? t("saving") : t("updatePassword")}
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}
