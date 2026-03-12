"""
CMS Models — Re-export all models for Alembic and convenience.
"""
from app.models.base import Base, TimestampMixin, SoftDeleteMixin

# Auth & RBAC
from app.models.user import CmsUser, CmsInvite
from app.models.permission import CmsContentType, CmsPermission
from app.models.group import CmsGroup, CmsUserPermission, cms_user_groups, cms_group_permissions

# Organization
from app.models.organization import CmsOrganization, CmsOrgMembership

# Agent & MCP
from app.models.agent import CmsAgent, CmsOrgAgent
from app.models.mcp import CmsMcpServer, CmsTool
from app.models.ui import CmsUIComponent
from app.models.resource_permission import CmsResourcePermission

# Provider
from app.models.provider import CmsProvider, CmsProviderKey, CmsAgentModel, CmsAgentProvider

# Knowledge
from app.models.folder import CmsFolder
from app.models.document import CmsDocument, CmsDocumentAccess, CmsAgentKnowledge, CmsKnowledgeIndexJob

# Other
from app.models.oauth import CmsOAuthConnection
from app.models.audit import CmsAuditLog
from app.models.system_setting import CmsSystemSetting

__all__ = [
    "Base", "TimestampMixin", "SoftDeleteMixin",
    "CmsUser", "CmsInvite",
    "CmsContentType", "CmsPermission",
    "CmsGroup", "CmsUserPermission", "cms_user_groups", "cms_group_permissions",
    "CmsOrganization", "CmsOrgMembership",
    "CmsAgent", "CmsOrgAgent",
    "CmsMcpServer", "CmsTool",
    "CmsUIComponent",
    "CmsResourcePermission",
    "CmsProvider", "CmsProviderKey", "CmsAgentModel", "CmsAgentProvider",
    "CmsFolder",
    "CmsDocument", "CmsDocumentAccess", "CmsAgentKnowledge", "CmsKnowledgeIndexJob",
    "CmsOAuthConnection",
    "CmsAuditLog",
    "CmsSystemSetting",
]
