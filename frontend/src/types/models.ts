/**
 * Entity model types — mirrors backend schemas.
 * All entity types used across the CMS frontend.
 */

// ============================================================================
// Organization
// ============================================================================

export interface Organization {
  id: string;
  name: string;
  slug: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface OrganizationListItem extends Organization {
  member_count: number;
}

export interface OrgCreateData {
  name: string;
  slug: string;
  timezone: string;
}

export interface OrgUpdateData {
  name?: string;
  slug?: string;
  timezone?: string;
}

// ============================================================================
// Agent (System)
// ============================================================================

export interface SystemAgent {
  id: string;
  codename: string;
  display_name: string;
  description: string | null;
  default_config: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface AgentCreateData {
  codename: string;
  display_name: string;
  description?: string;
  is_active?: boolean;
}

export interface AgentUpdateData {
  display_name?: string;
  description?: string;
  is_active?: boolean;
}

// ============================================================================
// Provider (System)
// ============================================================================

export interface SystemProvider {
  id: string;
  name: string;
  slug: string;
  api_base_url: string | null;
  auth_type: string;
  is_active: boolean;
  created_at: string;
}

export interface ProviderCreateData {
  name: string;
  slug: string;
  api_base_url?: string;
  auth_type: string;
  is_active?: boolean;
}

export interface ProviderUpdateData {
  name?: string;
  api_base_url?: string;
  auth_type?: string;
  is_active?: boolean;
}

// ============================================================================
// MCP Server (System)
// ============================================================================

export interface SystemMcpServer {
  id: string;
  codename: string;
  display_name: string;
  transport: string;
  connection_config: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface McpServerCreateData {
  codename: string;
  display_name: string;
  transport: string;
  connection_config?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface McpServerUpdateData {
  display_name?: string;
  transport?: string;
  connection_config?: Record<string, unknown> | null;
  is_active?: boolean;
}

// ============================================================================
// System Setting
// ============================================================================

export interface SystemSetting {
  id: string;
  key: string;
  value: string;
  description: string | null;
}

export interface SettingUpdateData {
  value: string;
}

// ============================================================================
// MCP Server Form State (used by system MCP page)
// ============================================================================

export interface McpFormState {
  codename: string;
  display_name: string;
  transport: string;
  connection_config_json: string;
  is_active: boolean;
}

// ============================================================================
// UI Permissions
// ============================================================================

export interface UIPermissions {
  user_id: string;
  org_id: string;
  nav_items: string[];
  actions: Record<string, string[]>;
}
