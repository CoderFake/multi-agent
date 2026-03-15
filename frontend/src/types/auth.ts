export interface LoginRequest {
  email: string;
  password: string;
}

export interface OrgMembership {
  org_id: string;
  org_name: string;
  org_slug: string;
  org_logo_url: string | null;
  org_role: string;
  is_active: boolean;
  timezone: string;
}

export interface MeResponse {
  id: string;
  email: string;
  full_name: string;
  is_superuser: boolean;
  is_active: boolean;
  avatar_url: string | null;
  memberships: OrgMembership[];
}

export interface Invite {
  id: string;
  email: string;
  org_id: string;
  org_role: string;
  status: "pending" | "accepted" | "expired" | "revoked";
  expires_at: string;
  created_at: string;
}