"use client";

import { useState, useRef, useEffect } from "react";
import { Camera, Loader2, Globe, Shield, Users, Building2, XIcon, ExternalLink } from "lucide-react";
import { useCurrentOrg } from "@/contexts/org-context";
import { useAuth } from "@/contexts/auth-context";
import { usePermissions } from "@/hooks/use-permissions";
import { useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import Link from "next/link";
import {
    updateOrgSettings,
    uploadOrgLogo,
    fetchTimezones,
} from "@/lib/api/tenant-settings";
import type { TimezoneOption } from "@/types/models";

interface OrgSettingsDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function OrgSettingsDialog({ open, onOpenChange }: OrgSettingsDialogProps) {
    const t = useTranslations("common");
    const tn = useTranslations("nav");
    const to = useTranslations("orgSettings");
    const { currentOrg, orgId, orgRole } = useCurrentOrg();
    const { user, refresh } = useAuth();
    const { hasPermission, isLoading: permLoading } = usePermissions();

    const canEdit = hasPermission("organization.update");

    // ── Local state ──
    const [name, setName] = useState("");
    const [timezone, setTimezone] = useState("");
    const [timezones, setTimezones] = useState<TimezoneOption[]>([]);
    const [saving, setSaving] = useState(false);
    const [avatarUploading, setAvatarUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    // Sync local state when org changes or dialog opens
    useEffect(() => {
        if (currentOrg && open) {
            setName(currentOrg.org_name);
            setTimezone(currentOrg.timezone || "UTC");
        }
    }, [currentOrg, open]);

    // Load timezones when dialog opens
    useEffect(() => {
        if (open && timezones.length === 0) {
            fetchTimezones()
                .then(setTimezones)
                .catch(() => {});
        }
    }, [open, timezones.length]);

    if (!currentOrg) return null;

    const tenantPrefix = orgId ? `/t/${orgId}` : "";
    const hasChanges = name !== currentOrg.org_name || timezone !== (currentOrg.timezone || "UTC");

    // ── Handlers ──
    const handleSave = async () => {
        if (!hasChanges) return;
        setSaving(true);
        try {
            const payload: Record<string, string> = {};
            if (name !== currentOrg.org_name) payload.name = name;
            if (timezone !== (currentOrg.timezone || "UTC")) payload.timezone = timezone;
            await updateOrgSettings(payload);
            await refresh();
            toast.success(to("updateSuccess"));
        } catch {
            toast.error(to("updateFailed"));
        } finally {
            setSaving(false);
        }
    };

    const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setAvatarUploading(true);
        try {
            await uploadOrgLogo(file);
            await refresh();
            toast.success(to("logoUploadSuccess"));
        } catch {
            toast.error(to("logoUploadFailed"));
        } finally {
            setAvatarUploading(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    };

    // ── Quick links ──
    const quickLinks = [
        { label: tn("users"), href: `${tenantPrefix}/users`, icon: Users },
        { label: tn("groups"), href: `${tenantPrefix}/groups`, icon: Shield },
        { label: tn("agents"), href: `${tenantPrefix}/agents`, icon: Building2 },
    ];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                className="max-w-md gap-0 overflow-hidden bg-sidebar p-0"
                showCloseButton={false}
                onOpenAutoFocus={(e) => e.preventDefault()}
            >
                <DialogTitle className="sr-only">{to("title")}</DialogTitle>

                {/* Close button */}
                <button
                    onClick={() => onOpenChange(false)}
                    className="absolute top-3 right-3 z-10 rounded-sm p-1 opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-none"
                >
                    <XIcon className="size-4" />
                    <span className="sr-only">Close</span>
                </button>

                {/* Header — org avatar + name */}
                <div className="flex flex-col items-center gap-3 px-6 pt-8 pb-5 bg-gradient-to-b from-primary/5 to-transparent">
                    {/* Avatar — editable if has permission */}
                    <div className="relative group">
                        {currentOrg.org_logo_url ? (
                            <img
                                src={currentOrg.org_logo_url}
                                alt={currentOrg.org_name}
                                className="h-16 w-16 rounded-xl object-cover shadow-md ring-2 ring-background"
                            />
                        ) : (
                            <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary text-primary-foreground text-2xl font-bold shadow-md">
                                {currentOrg.org_name.charAt(0).toUpperCase()}
                            </div>
                        )}

                        {canEdit && (
                            <>
                                <button
                                    type="button"
                                    onClick={() => fileRef.current?.click()}
                                    disabled={avatarUploading}
                                    className="absolute inset-0 flex items-center justify-center rounded-xl bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
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
                            </>
                        )}
                    </div>

                    <div className="text-center">
                        <h3 className="text-lg font-semibold">{currentOrg.org_name}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">{currentOrg.org_slug}</p>
                    </div>
                    <Badge
                        variant={currentOrg.is_active ? "default" : "secondary"}
                        className="text-[10px]"
                    >
                        {currentOrg.is_active ? t("active") : t("inactive")}
                    </Badge>
                </div>

                {/* Editable settings */}
                <div className="px-6 py-4 space-y-4 bg-background">
                    {/* Read-only notice for users without permission */}
                    {!permLoading && !canEdit && (
                        <p className="text-xs text-muted-foreground bg-muted/50 rounded-md px-3 py-2">
                            {to("readOnly")}
                        </p>
                    )}

                    {/* Organization Name */}
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-foreground">{to("orgName")}</label>
                        <p className="text-xs text-muted-foreground">{to("orgNameDesc")}</p>
                        {canEdit ? (
                            <Input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="h-9 text-sm"
                            />
                        ) : (
                            <p className="text-sm text-muted-foreground py-1">{currentOrg.org_name}</p>
                        )}
                    </div>

                    {/* Timezone */}
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-foreground">{to("timezone")}</label>
                        <p className="text-xs text-muted-foreground">{to("timezoneDesc")}</p>
                        {canEdit ? (
                            <Select value={timezone} onValueChange={setTimezone}>
                                <SelectTrigger className="h-9 text-sm">
                                    <SelectValue placeholder={to("selectTimezone")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {timezones.map((tz) => (
                                        <SelectItem key={tz.value} value={tz.value}>
                                            {tz.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        ) : (
                            <p className="text-sm text-muted-foreground py-1">
                                {timezones.find((tz) => tz.value === (currentOrg.timezone || "UTC"))?.label || currentOrg.timezone || "UTC"}
                            </p>
                        )}
                    </div>

                    {/* Save button */}
                    {canEdit && (
                        <Button
                            onClick={handleSave}
                            disabled={saving || !hasChanges}
                            className="w-full h-9"
                            size="sm"
                        >
                            {saving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {to("saving")}
                                </>
                            ) : (
                                to("save")
                            )}
                        </Button>
                    )}
                </div>

                {/* Info rows + quick links */}
                <div className="px-6 py-4 border-t border-border/50 bg-background space-y-3">
                    {/* Role & Account (read-only info) */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
                            <Shield className="h-4 w-4" />
                            <span>{to("yourRole")}</span>
                        </div>
                        <Badge variant="outline" className="text-xs capitalize">
                            {orgRole}
                        </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
                            <Users className="h-4 w-4" />
                            <span>{to("account")}</span>
                        </div>
                        <span className="text-sm font-medium truncate max-w-[180px]">
                            {user?.email ?? "—"}
                        </span>
                    </div>
                </div>

                {/* Quick links */}
                <div className="px-6 py-4 border-t border-border/50 bg-background">
                    <p className="text-xs font-medium text-muted-foreground mb-2.5">
                        {to("quickLinks")}
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                        {quickLinks.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                onClick={() => onOpenChange(false)}
                                className="flex flex-col items-center gap-1.5 rounded-lg border border-border/50 bg-card p-3 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                            >
                                <link.icon className="h-4 w-4" />
                                <span>{link.label}</span>
                                <ExternalLink className="h-3 w-3 opacity-50" />
                            </Link>
                        ))}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
