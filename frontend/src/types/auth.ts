export interface LoginRequest {
  email: string;
  password: string;
}

export interface OrgMembership {
  org_id: string;
  org_name: string;
  org_slug: string;
  org_role: string;
  is_active: boolean;
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
