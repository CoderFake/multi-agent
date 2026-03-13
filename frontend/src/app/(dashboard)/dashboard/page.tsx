"use client";

import { useAuth } from "@/contexts/auth-context";
import { useCurrentOrg } from "@/contexts/org-context";
import { useTranslations } from "next-intl";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Building2, Users, Bot, Activity } from "lucide-react";

const stats = [
  { key: "totalOrgs", icon: Building2, value: "—", color: "text-blue-500" },
  { key: "totalUsers", icon: Users, value: "—", color: "text-emerald-500" },
  { key: "totalAgents", icon: Bot, value: "—", color: "text-violet-500" },
  { key: "activeSessions", icon: Activity, value: "—", color: "text-amber-500" },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const { currentOrg, isSuperuser } = useCurrentOrg();
  const t = useTranslations("dashboard");

  return (
    <div>
      <PageHeader
        title={t("title")}
        description={t("welcome", { name: user?.full_name ?? "" })}
      />

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.key} className="relative overflow-hidden transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className={`rounded-lg bg-gradient-to-br from-muted to-muted/50 p-3 ${stat.color}`}>
                <stat.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-xs text-muted-foreground">{t(stat.key)}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">{t("account")}</h3>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>{t("email")}: {user?.email}</p>
              <p>{t("role")}: {isSuperuser ? t("superuser") : currentOrg?.org_role ?? "—"}</p>
              <p>{t("org")}: {currentOrg?.org_name ?? t("noOrganization")}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">{t("quickActions")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("quickActionsDesc")}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
