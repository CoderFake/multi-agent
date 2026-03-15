"use client";

import { useState, useCallback, useMemo } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { ColumnDef } from "@tanstack/react-table";
import {
    createInvite,
    fetchInvites,
    revokeInvite,
    resendInvite,
} from "@/lib/api/system";
import type { Invite } from "@/types/models";
import { formatDateTime } from "@/lib/datetime";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import { DataTable } from "@/components/data-table/data-table";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { UserPlus, RotateCw } from "lucide-react";

const ROLES = ["owner", "admin", "member"] as const;
const ROLE_LEVEL: Record<string, number> = { member: 1, admin: 2, owner: 3 };

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    pending: "outline",
    accepted: "default",
    expired: "secondary",
    revoked: "destructive",
};

interface UserInviteListProps {
    onMembersMutate?: () => void;
}

export function UserInviteList({ onMembersMutate }: UserInviteListProps) {
    const t = useTranslations("common");
    const tu = useTranslations("tenant");
    const { orgId, orgRole } = useCurrentOrg();
    const { hasPermission } = usePermissions();
    const isSuperuser = orgRole === "superuser";
    const myLevel = isSuperuser ? 99 : (ROLE_LEVEL[orgRole ?? ""] ?? 0);

    // Invite dialog
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteRole, setInviteRole] = useState<string>("member");
    const [inviting, setInviting] = useState(false);

    // Revoke dialog
    const [revokeTarget, setRevokeTarget] = useState<Invite | null>(null);

    // Resending state
    const [resendingId, setResendingId] = useState<string | null>(null);

    const { data: invites, mutate: mutateInvites } = useSWR(
        orgId ? ["org-invites", orgId] : null,
        () => fetchInvites(orgId!),
    );

    // Sort: pending first, then by created_at desc
    const sortedInvites = useMemo(() => {
        if (!invites) return [];
        return [...invites].sort((a, b) => {
            if (a.status === "pending" && b.status !== "pending") return -1;
            if (a.status !== "pending" && b.status === "pending") return 1;
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
    }, [invites]);

    const columns: ColumnDef<Invite, unknown>[] = [
        {
            accessorKey: "email",
            header: t("email"),
            cell: ({ row }) => (
                <span className="font-medium text-sm">{row.original.email}</span>
            ),
        },
        {
            accessorKey: "org_role",
            header: tu("role"),
            cell: ({ row }) => (
                <Badge variant="outline">{row.original.org_role}</Badge>
            ),
        },
        {
            accessorKey: "status",
            header: t("status"),
            cell: ({ row }) => (
                <Badge variant={STATUS_VARIANTS[row.original.status] ?? "outline"}>
                    {tu(`inviteStatus_${row.original.status}`)}
                </Badge>
            ),
        },
        {
            accessorKey: "created_at",
            header: tu("invitedAt"),
            cell: ({ row }) => formatDateTime(row.original.created_at),
        },
        {
            accessorKey: "expires_at",
            header: tu("expiresAt"),
            cell: ({ row }) => formatDateTime(row.original.expires_at),
        },
        {
            id: "actions",
            header: "",
            cell: ({ row }) => {
                const inv = row.original;
                if (inv.status !== "pending") return null;

                return (
                    <div className="flex items-center gap-1">
                        {hasPermission("invite.resend") && (
                            <Button
                                size="sm"
                                variant="ghost"
                                className="gap-1 h-7 text-xs"
                                disabled={resendingId === inv.id}
                                onClick={async () => {
                                    setResendingId(inv.id);
                                    try {
                                        await resendInvite(inv.id);
                                        toast.success(tu("inviteResent"));
                                        mutateInvites();
                                    } catch {
                                        toast.error(t("error"));
                                    } finally {
                                        setResendingId(null);
                                    }
                                }}
                            >
                                <RotateCw className="h-3 w-3" />
                                {tu("resend")}
                            </Button>
                        )}
                        {hasPermission("invite.revoke") && (
                            <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs text-destructive hover:text-destructive"
                                onClick={() => setRevokeTarget(inv)}
                            >
                                {tu("revoke")}
                            </Button>
                        )}
                    </div>
                );
            },
        },
    ];

    // Invite handler
    const handleInvite = useCallback(async () => {
        if (!orgId) return;
        setInviting(true);
        try {
            await createInvite({ email: inviteEmail, org_id: orgId, org_role: inviteRole });
            toast.success(tu("inviteSent"));
            setInviteOpen(false);
            setInviteEmail("");
            setInviteRole("member");
            mutateInvites();
            onMembersMutate?.();
        } catch {
            toast.error(t("error"));
        } finally {
            setInviting(false);
        }
    }, [orgId, inviteEmail, inviteRole, mutateInvites, onMembersMutate, tu, t]);

    // Revoke handler
    const handleRevoke = useCallback(async () => {
        if (!revokeTarget) return;
        try {
            await revokeInvite(revokeTarget.id);
            toast.success(tu("inviteRevoked"));
            setRevokeTarget(null);
            mutateInvites();
        } catch {
            toast.error(t("error"));
        }
    }, [revokeTarget, mutateInvites, tu, t]);

    return (
        <>
            <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-muted-foreground">
                    {tu("inviteListDesc")}
                </p>
                {hasPermission("invite.create") && (
                    <Button onClick={() => setInviteOpen(true)} className="gap-2" size="sm">
                        <UserPlus className="h-4 w-4" />
                        {tu("inviteUser")}
                    </Button>
                )}
            </div>

            <DataTable
                columns={columns}
                data={sortedInvites}
                total={sortedInvites.length}
                page={1}
                pageSize={100}
                onPageChange={() => { }}
                isLoading={!invites}
            />

            {/* Invite Dialog */}
            <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{tu("inviteUser")}</DialogTitle>
                        <DialogDescription>{tu("inviteUserDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label>{t("email")}</Label>
                            <Input
                                type="email"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                                placeholder="user@example.com"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>{tu("role")}</Label>
                            <Select value={inviteRole} onValueChange={setInviteRole}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ROLES.filter((r) => isSuperuser || ROLE_LEVEL[r] < myLevel).map((r) => (
                                        <SelectItem key={r} value={r}>
                                            {r}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setInviteOpen(false)}>
                            {t("cancel")}
                        </Button>
                        <Button onClick={handleInvite} disabled={inviting || !inviteEmail}>
                            {inviting ? t("processing") : tu("sendInvite")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Revoke Confirmation */}
            <ConfirmDialog
                open={!!revokeTarget}
                onOpenChange={(open) => !open && setRevokeTarget(null)}
                title={tu("revokeInviteTitle")}
                description={tu("revokeInviteDesc")}
                onConfirm={handleRevoke}
            />
        </>
    );
}
