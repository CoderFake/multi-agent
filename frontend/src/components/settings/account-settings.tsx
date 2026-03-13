"use client";

import { useState, useRef } from "react";
import { Camera, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { useCurrentOrg } from "@/contexts/org-context";
import { useTranslations } from "next-intl";
import { uploadAvatar } from "@/lib/auth";
import { toast } from "sonner";

function SettingsRow({
    label,
    description,
    children,
}: {
    label: string;
    description?: string;
    children: React.ReactNode;
}) {
    return (
        <div className="flex items-center justify-between gap-6 py-4">
            <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">{label}</p>
                {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
            </div>
            <div className="shrink-0">{children}</div>
        </div>
    );
}

export function AccountSettings() {
    const { user, refresh } = useAuth();
    const { orgRole } = useCurrentOrg();
    const t = useTranslations("settings");

    const [name, setName] = useState(user?.full_name || "");
    const [profileLoading, setProfileLoading] = useState(false);
    const [profileSuccess, setProfileSuccess] = useState(false);
    const [avatarUploading, setAvatarUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    const handleProfileSubmit = async () => {
        setProfileLoading(true);
        try {
            // TODO: call API to update profile
            await new Promise((r) => setTimeout(r, 500));
            setProfileSuccess(true);
            setTimeout(() => setProfileSuccess(false), 3000);
        } finally {
            setProfileLoading(false);
        }
    };

    const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setAvatarUploading(true);
        try {
            await uploadAvatar(file);
            await refresh(); // re-fetch /me to get new avatar_url
            toast.success(t("avatarUploadSuccess"));
        } catch {
            toast.error(t("avatarUploadFailed"));
        } finally {
            setAvatarUploading(false);
            // Reset file input so same file can be re-selected
            if (fileRef.current) fileRef.current.value = "";
        }
    };

    if (!user) return null;

    return (
        <div className="space-y-0">
            {/* Profile Header with Avatar */}
            <div className="flex flex-col items-center py-6">
                <div className="relative group">
                    {user.avatar_url ? (
                        <img
                            src={user.avatar_url}
                            alt={user.full_name || "Avatar"}
                            className="h-16 w-16 rounded-full object-cover border-2 border-border"
                        />
                    ) : (
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary/80 to-violet-500 text-xl font-bold text-white">
                            {user.full_name?.charAt(0).toUpperCase() ?? "U"}
                        </div>
                    )}

                    {/* Overlay hover */}
                    <button
                        type="button"
                        onClick={() => fileRef.current?.click()}
                        disabled={avatarUploading}
                        className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                    >
                        {avatarUploading ? (
                            <Loader2 className="h-5 w-5 animate-spin text-white" />
                        ) : (
                            <Camera className="h-5 w-5 text-white" />
                        )}
                    </button>

                    <input
                        ref={fileRef}
                        type="file"
                        accept="image/jpeg,image/png,image/gif,image/webp"
                        onChange={handleAvatarChange}
                        className="hidden"
                    />
                </div>
                <div className="mt-3 text-center">
                    <p className="text-lg font-medium">{user.full_name || "User"}</p>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("avatarDesc")}</p>
                </div>
            </div>

            <div className="border-b border-border/40" />

            {/* Display Name */}
            <SettingsRow label={t("displayName")} description={t("displayNameDesc")}>
                <div className="flex items-center">
                    <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder={t("yourName")}
                        className="h-9 w-44 rounded-r-none border-r-0 text-sm focus-visible:z-10"
                    />
                    <Button
                        size="sm"
                        onClick={handleProfileSubmit}
                        disabled={profileLoading || name === user.full_name}
                        className="h-9 rounded-l-none px-4"
                    >
                        {profileLoading ? (
                            <Loader2 className="size-4 animate-spin" />
                        ) : profileSuccess ? (
                            t("saved")
                        ) : (
                            t("save")
                        )}
                    </Button>
                </div>
            </SettingsRow>

            <div className="border-b border-border/40" />

            {/* Email */}
            <SettingsRow label={t("email")} description={t("emailDesc")}>
                <p className="text-sm text-muted-foreground">{user.email}</p>
            </SettingsRow>

            <div className="border-b border-border/40" />

            {/* Role */}
            <SettingsRow label={t("role")} description={t("roleDesc")}>
                <p className="text-sm text-muted-foreground capitalize">
                    {user.is_superuser ? "Superuser" : orgRole || "User"}
                </p>
            </SettingsRow>
        </div>
    );
}
