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
  subdomain?: string;
  timezone: string;
  is_active: boolean;
  logo_url?: string;
  created_at: string;
  updated_at?: string;
}

export interface OrganizationListItem extends Organization {
  member_count: number;
}

export interface OrgCreateData {
  name: string;
  subdomain: string;
  timezone: string;
}

export interface OrgUpdateData {
  name?: string;
  subdomain?: string;
  timezone?: string;
  is_active?: boolean;
}

export interface OrgMember {
  user_id: string;
  user_email: string;
  user_full_name: string;
  org_role: string;
  is_active: boolean;
  joined_at: string;
}

export interface AddMemberData {
  user_id: string;
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
  is_public: boolean;
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
  is_public?: boolean;
}

export interface AgentOrgItem {
  org_id: string;
  org_name: string;
  is_enabled: boolean;
}

export interface AgentToolItem {
  id: string;
  codename: string;
  display_name: string;
  description: string | null;
  server_name: string;
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
  requires_env_vars: boolean;
  is_active: boolean;
  is_public: boolean;
  created_at: string;
}

export interface McpServerCreateData {
  codename: string;
  display_name: string;
  transport: string;
  connection_config?: Record<string, unknown> | null;
  requires_env_vars?: boolean;
  is_active?: boolean;
  is_public?: boolean;
}

export interface McpServerUpdateData {
  display_name?: string;
  transport?: string;
  connection_config?: Record<string, unknown> | null;
  requires_env_vars?: boolean;
  is_active?: boolean;
  is_public?: boolean;
}

export interface DiscoveredTool {
  name: string;
  description: string | null;
  input_schema: Record<string, unknown> | null;
}

export interface McpDiscoverResponse {
  server_name: string;
  tools: DiscoveredTool[];
  error: string | null;
}

export interface McpToolResponse {
  id: string;
  mcp_server_id: string;
  codename: string;
  display_name: string;
  description: string | null;
  input_schema: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
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

// ============================================================================
// Notification
// ============================================================================

export interface Notification {
  id: string;
  type: string;
  title_code: string;
  message_code: string | null;
  data: Record<string, string> | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

// ============================================================================
// Feedback
// ============================================================================

export interface Feedback {
  id: string;
  user_id: string;
  user_email: string | null;
  user_full_name: string | null;
  category: string;
  message: string;
  attachments: string[] | null;
  status: string;
  created_at: string;
}

export interface FeedbackListResponse {
  items: Feedback[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// Tenant User (org-scoped)
// ============================================================================

export interface TenantUser {
  user_id: string;
  email: string;
  full_name: string;
  org_role: string;
  is_active: boolean;
  joined_at: string | null;
}

export interface TenantUserUpdate {
  org_role?: string;
  is_active?: boolean;
}

// ============================================================================
// Tenant Group
// ============================================================================

export interface Group {
  id: string;
  org_id: string | null;
  name: string;
  description: string | null;
  is_system_default: boolean;
  member_count: number;
  permission_count: number;
}

export interface GroupCreate {
  name: string;
  description?: string;
}

export interface GroupUpdate {
  name?: string;
  description?: string;
}

// ============================================================================
// Permission
// ============================================================================

export interface Permission {
  id: string;
  codename: string;
  name: string;
  app_label: string;
  model: string;
}

// ============================================================================
// Audit Log
// ============================================================================

export interface AuditLog {
  id: string;
  user_id: string;
  user_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  created_at: string;
}

// ============================================================================
// Agent
// ============================================================================

export interface Agent {
  id: string;
  codename: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  is_system: boolean;
  is_enabled: boolean;
  is_public: boolean;
}

export interface AgentCreate {
  codename: string;
  display_name: string;
  description?: string;
  default_config?: Record<string, unknown>;
}

export interface AgentUpdate {
  display_name?: string;
  description?: string;
  default_config?: Record<string, unknown>;
  is_active?: boolean;
}

// ============================================================================
// Agent Access Control
// ============================================================================

export interface AgentMcpServer {
  id: string;
  agent_id: string;
  mcp_server_id: string;
  mcp_server_codename: string;
  mcp_server_name: string;
  is_active: boolean;
  env_overrides: Record<string, string> | null;
  requires_env_vars: boolean;
  connection_config: Record<string, unknown> | null;
}

export interface AvailableMcpServer {
    id: string;
    codename: string;
    display_name: string;
    transport: string;
    requires_env_vars: boolean;
}

export interface GroupAgent {
  id: string;
  group_id: string;
  agent_id: string;
  agent_codename: string;
  agent_name: string;
}

export interface GroupToolAccess {
  id: string;
  group_id: string;
  tool_id: string;
  tool_codename: string;
  tool_name: string;
  is_enabled: boolean;
}
