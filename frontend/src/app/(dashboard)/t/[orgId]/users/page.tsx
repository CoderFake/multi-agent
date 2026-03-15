"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { fetchTenantUsers } from "@/lib/api/tenant";
import { useCurrentOrg } from "@/contexts/org-context";
import { PermissionGate } from "@/components/shared/permission-gate";
import { usePermissions } from "@/hooks/use-permissions";
import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UserMemberList } from "@/components/users/user-member-list";
import { UserInviteList } from "@/components/users/user-invite-list";

export default function TenantUsersPage() {
    const t = useTranslations("common");
    const tu = useTranslations("tenant");
    const { orgId, orgRole } = useCurrentOrg();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const { hasPermission } = usePermissions();
    const canViewInvites = hasPermission("invite.view");

    const { data, mutate, isLoading } = useSWR(
        orgId ? ["tenant-users", orgId, page, search] : null,
        () => fetchTenantUsers({ page, pageSize: 20, search: search || undefined }),
    );

    return (
        <PermissionGate permission="user.view" pageLevel>
            <div>
                <PageHeader title={tu("usersTitle")} description={tu("usersDesc")} />

                <Tabs defaultValue="members" className="mt-4">
                    <TabsList>
                        <TabsTrigger value="members">
                            {t("members")} ({data?.total ?? 0})
                        </TabsTrigger>
                        {canViewInvites && (
                            <TabsTrigger value="invites">
                                {tu("invites")}
                            </TabsTrigger>
                        )}
                    </TabsList>

                    <TabsContent value="members">
                        <UserMemberList
                            orgRole={orgRole}
                            data={data}
                            page={page}
                            onPageChange={setPage}
                            search={search}
                            onSearch={setSearch}
                            isLoading={isLoading}
                            onMutate={mutate}
                        />
                    </TabsContent>

                    {canViewInvites && (
                        <TabsContent value="invites">
                            <UserInviteList onMembersMutate={mutate} />
                        </TabsContent>
                    )}
                </Tabs>
            </div>
        </PermissionGate>
    );
}
