"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { OrgUpdateData } from "@/types/models";
import type { ApiError } from "@/lib/api-client";
import {
    fetchOrganization,
    updateOrganization,
    fetchOrgMembers,
    fetchTimezones,
    uploadOrgLogo,
    createInvite,
    fetchInvites,
    revokeInvite,
    resendInvite,
} from "@/lib/api/system";
import { formatDateTime } from "@/lib/datetime";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    ArrowLeft,
    Building,
    Globe,
    Clock,
    Save,
    UserPlus,
    Users,
    Loader2,
    Camera,
    Mail,
    RotateCcw,
    XCircle,
    Send,
} from "lucide-react";

type TabType = "overview" | "members";

export default function OrganizationDetailPage() {
    const t = useTranslations("common");
    const ts = useTranslations("system");
    const te = useTranslations("errors");
    const router = useRouter();
    const params = useParams();
    const orgId = params.id as string;

    const [activeTab, setActiveTab] = useState<TabType>("overview");
    const [saving, setSaving] = useState(false);

    // Invite dialog state
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviting, setInviting] = useState(false);

    // Logo upload
    const logoInputRef = useRef<HTMLInputElement>(null);
    const [uploadingLogo, setUploadingLogo] = useState(false);

    // Org data
    const {
        data: org,
        mutate: mutateOrg,
        isLoading: orgLoading,
    } = useSWR(orgId ? `org-${orgId}` : null, () => fetchOrganization(orgId));

    // Org members
    const {
        data: members,
        isLoading: membersLoading,
    } = useSWR(
        orgId && activeTab === "members" ? `org-members-${orgId}` : null,
        () => fetchOrgMembers(orgId),
    );

    // Invites
    const {
        data: invites,
        mutate: mutateInvites,
    } = useSWR(
        orgId && activeTab === "members" ? `org-invites-${orgId}` : null,
        () => fetchInvites(orgId),
    );

    // Timezones
    const { data: timezones } = useSWR("timezones", fetchTimezones);

    // Edit form state (subdomain NOT editable)
    const [formData, setFormData] = useState<OrgUpdateData>({});

    useEffect(() => {
        if (org) {
            setFormData({
                name: org.name,
                timezone: org.timezone,
            });
        }
    }, [org]);

    const handleSave = useCallback(async () => {
        setSaving(true);
        try {
            await updateOrganization(orgId, formData);
            toast.success(t("updateSuccess"));
            mutateOrg();
        } catch (err: unknown) {
            const apiErr = err as ApiError;
            toast.error(te(apiErr.error_code || "UNKNOWN_ERROR"));
        } finally {
            setSaving(false);
        }
    }, [orgId, formData, mutateOrg, t, te]);

    // ── Logo Upload ─────────────────────────────────────────────────────
    const handleLogoUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploadingLogo(true);
        try {
            await uploadOrgLogo(orgId, file);
            toast.success(ts("logoUpdated"));
            mutateOrg();
        } catch {
            toast.error(ts("logoUploadFailed"));
        } finally {
            setUploadingLogo(false);
            if (logoInputRef.current) logoInputRef.current.value = "";
        }
    }, [orgId, mutateOrg, ts]);

    // ── Invite Owner ────────────────────────────────────────────────────
    const handleInvite = useCallback(async () => {
        if (!inviteEmail.trim()) return;
        setInviting(true);
        try {
            await createInvite({
                email: inviteEmail.trim(),
                org_id: orgId,
                org_role: "owner",
            });
            toast.success(ts("inviteSent", { email: inviteEmail }));
            setInviteOpen(false);
            setInviteEmail("");
            mutateInvites();
        } catch (err: unknown) {
            const apiErr = err as ApiError;
            toast.error(te(apiErr.error_code || "INVITE_SEND_FAILED"));
        } finally {
            setInviting(false);
        }
    }, [orgId, inviteEmail, mutateInvites, ts, te]);

    const handleRevokeInvite = useCallback(async (inviteId: string) => {
        try {
            await revokeInvite(inviteId);
            toast.success(ts("inviteRevoked"));
            mutateInvites();
        } catch (err: unknown) {
            const apiErr = err as ApiError;
            toast.error(te(apiErr.error_code || "INVITE_REVOKE_FAILED"));
        }
    }, [mutateInvites, ts, te]);

    const handleResendInvite = useCallback(async (inviteId: string) => {
        try {
            await resendInvite(inviteId);
            toast.success(ts("inviteResent"));
            mutateInvites();
        } catch (err: unknown) {
            const apiErr = err as ApiError;
            toast.error(te(apiErr.error_code || "INVITE_RESEND_FAILED"));
        }
    }, [mutateInvites, ts, te]);

    if (orgLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!org) {
        return (
            <div className="p-6">
                <p className="text-destructive">{t("noData")}</p>
            </div>
        );
    }

    const pendingInvites = invites?.filter((i) => i.status === "pending") ?? [];
    const otherInvites = invites?.filter((i) => i.status !== "pending") ?? [];

    return (
        <div className="max-w-5xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <button
                    onClick={() => router.push("/system/organizations")}
                    className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-4 text-sm"
                >
                    <ArrowLeft className="w-4 h-4" />
                    {t("back")}
                </button>

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        {/* Logo Upload */}
                        <div
                            className="relative w-14 h-14 rounded-lg overflow-hidden bg-primary/10 flex items-center justify-center cursor-pointer group"
                            onClick={() => logoInputRef.current?.click()}
                        >
                            {org.logo_url ? (
                                <img src={org.logo_url} alt={org.name} className="w-full h-full object-cover" />
                            ) : (
                                <Building className="w-7 h-7 text-primary" />
                            )}
                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                {uploadingLogo ? (
                                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                                ) : (
                                    <Camera className="w-5 h-5 text-white" />
                                )}
                            </div>
                            <input
                                ref={logoInputRef}
                                type="file"
                                accept="image/jpeg,image/png,image/gif,image/webp"
                                className="hidden"
                                onChange={handleLogoUpload}
                            />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold">{org.name}</h1>
                            <p className="text-muted-foreground text-sm">
                                {org.subdomain || org.slug}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="mb-6 border-b border-border">
                <div className="flex gap-4">
                    <button
                        onClick={() => setActiveTab("overview")}
                        className={`px-4 py-2 border-b-2 transition-colors text-sm font-medium ${activeTab === "overview"
                            ? "border-primary text-primary"
                            : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {ts("tabOverview")}
                    </button>
                    <button
                        onClick={() => setActiveTab("members")}
                        className={`px-4 py-2 border-b-2 transition-colors text-sm font-medium ${activeTab === "members"
                            ? "border-primary text-primary"
                            : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {ts("tabMembers")}
                    </button>
                </div>
            </div>

            {/* Overview Tab */}
            {activeTab === "overview" && (
                <>
                    {/* Info Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <Card>
                            <CardContent className="pt-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-violet-100 dark:bg-violet-900/30 rounded-lg flex items-center justify-center">
                                        <Globe className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">{ts("subdomain")}</p>
                                        <p className="font-medium">{org.subdomain || org.slug}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent className="pt-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                                        <Clock className="w-5 h-5 text-green-600 dark:text-green-400" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">{t("timezone")}</p>
                                        <p className="font-medium">{org.timezone}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent className="pt-4">
                                <div className="flex items-center gap-3">
                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${org.is_active
                                        ? "bg-green-100 dark:bg-green-900/30"
                                        : "bg-red-100 dark:bg-red-900/30"
                                        }`}>
                                        <div className={`w-3 h-3 rounded-full ${org.is_active ? "bg-green-500" : "bg-red-500"
                                            }`} />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">{t("status")}</p>
                                        <p className={`font-medium ${org.is_active ? "text-green-600" : "text-red-600"
                                            }`}>
                                            {org.is_active ? t("active") : t("inactive")}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Edit Form — subdomain is read-only */}
                    <Card>
                        <CardHeader>
                            <CardTitle>{ts("editOrg")}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label>{t("name")}</Label>
                                    <Input
                                        value={formData.name || ""}
                                        onChange={(e) =>
                                            setFormData({ ...formData, name: e.target.value })
                                        }
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>{t("timezone")}</Label>
                                    <select
                                        value={formData.timezone || "UTC"}
                                        onChange={(e) =>
                                            setFormData({ ...formData, timezone: e.target.value })
                                        }
                                        className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-2 focus-visible:border-muted-foreground/70"
                                    >
                                        {(timezones ?? []).map((tz) => (
                                            <option key={tz.value} value={tz.value}>
                                                {tz.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="flex justify-end gap-3 pt-4 border-t border-border">
                                    <Button
                                        variant="outline"
                                        onClick={() => router.push("/system/organizations")}
                                        disabled={saving}
                                    >
                                        {t("cancel")}
                                    </Button>
                                    <Button onClick={handleSave} disabled={saving} className="gap-2">
                                        {saving ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Save className="h-4 w-4" />
                                        )}
                                        {t("save")}
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            {/* Members Tab */}
            {activeTab === "members" && (
                <div className="space-y-6">
                    {/* Header + Invite Button */}
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold">{ts("tabMembers")}</h2>
                        <Button onClick={() => setInviteOpen(true)} className="gap-2">
                            <UserPlus className="h-4 w-4" />
                            {ts("inviteOwner")}
                        </Button>
                    </div>

                    {/* Pending Invites */}
                    {pendingInvites.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Send className="w-4 h-4" />
                                    {ts("pendingInvitations")} ({pendingInvites.length})
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="divide-y divide-border">
                                    {pendingInvites.map((invite) => (
                                        <div key={invite.id} className="flex items-center justify-between px-6 py-3">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center">
                                                    <Mail className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                                                </div>
                                                <div>
                                                    <p className="text-sm font-medium">{invite.email}</p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {ts("expires", { date: formatDateTime(invite.expires_at) })}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleResendInvite(invite.id)}
                                                    className="gap-1 text-xs"
                                                >
                                                    <RotateCcw className="w-3 h-3" />
                                                    {ts("resend")}
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleRevokeInvite(invite.id)}
                                                    className="gap-1 text-xs text-destructive hover:text-destructive"
                                                >
                                                    <XCircle className="w-3 h-3" />
                                                    {ts("revoke")}
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Members List */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base flex items-center gap-2">
                                <Users className="w-4 h-4" />
                                {t("members")}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {membersLoading ? (
                                <div className="flex justify-center py-12">
                                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                                </div>
                            ) : !members || members.length === 0 ? (
                                <div className="text-center py-12">
                                    <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                                    <p className="text-muted-foreground">{ts("noMembers")}</p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-border">
                                        <thead className="bg-muted/50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    {t("name")}
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    {ts("email")}
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    {ts("role")}
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    {t("status")}
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    {ts("joined")}
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border">
                                            {members.map((member) => (
                                                <tr key={member.user_id} className="hover:bg-muted/50">
                                                    <td className="px-6 py-4 text-sm font-medium">
                                                        {member.user_full_name}
                                                    </td>
                                                    <td className="px-6 py-4 text-sm text-muted-foreground">
                                                        {member.user_email}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-primary/10 text-primary capitalize">
                                                            {member.org_role}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${member.is_active
                                                            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                                                            : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                                                            }`}>
                                                            {member.is_active ? t("active") : t("inactive")}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-sm text-muted-foreground">
                                                        {formatDateTime(member.joined_at)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Invite History */}
                    {otherInvites.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base">{ts("inviteHistory")}</CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="divide-y divide-border">
                                    {otherInvites.map((invite) => (
                                        <div key={invite.id} className="flex items-center justify-between px-6 py-3">
                                            <div>
                                                <p className="text-sm">{invite.email}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {formatDateTime(invite.created_at)}
                                                </p>
                                            </div>
                                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${invite.status === "accepted"
                                                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                                                : invite.status === "expired"
                                                    ? "bg-muted text-muted-foreground"
                                                    : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                                                }`}>
                                                {invite.status}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Invite Owner Dialog */}
                    <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                        <DialogContent className="sm:max-w-md">
                            <DialogHeader>
                                <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                                    <UserPlus className="w-6 h-6 text-primary" />
                                </div>
                                <DialogTitle className="text-center text-xl">
                                    {ts("inviteOwner")}
                                </DialogTitle>
                                <p className="text-center text-sm text-muted-foreground mt-1">
                                    {ts("inviteOwnerDesc", { orgName: org.name })}
                                </p>
                            </DialogHeader>

                            <form
                                onSubmit={(e) => { e.preventDefault(); handleInvite(); }}
                                className="space-y-5 pt-2"
                            >
                                {/* Email Field */}
                                <div className="space-y-2">
                                    <Label htmlFor="invite-email" className="text-sm font-medium">
                                        {ts("email")} <span className="text-destructive">*</span>
                                    </Label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                        <Input
                                            id="invite-email"
                                            type="email"
                                            required
                                            value={inviteEmail}
                                            onChange={(e) => setInviteEmail(e.target.value)}
                                            placeholder="owner@example.com"
                                            disabled={inviting}
                                            className="pl-10"
                                        />
                                    </div>
                                </div>

                                {/* Note */}
                                <div className="flex gap-3 p-3 rounded-lg bg-muted/50 border border-border">
                                    <div className="shrink-0 mt-0.5">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-muted-foreground">
                                            <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        {ts("inviteNote")}
                                    </p>
                                </div>

                                {/* Actions */}
                                <DialogFooter className="gap-2 sm:gap-0">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={() => setInviteOpen(false)}
                                        disabled={inviting}
                                    >
                                        {t("cancel")}
                                    </Button>
                                    <Button
                                        type="submit"
                                        disabled={inviting || !inviteEmail.trim()}
                                        className="gap-2"
                                    >
                                        {inviting ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Send className="h-4 w-4" />
                                        )}
                                        {inviting ? ts("sending") : ts("sendInvitation")}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>
            )}
        </div>
    );
}
