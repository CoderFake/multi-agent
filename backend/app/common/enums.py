"""
Centralized enumerations for the CMS backend.
All Enums should be defined here for consistency and reusability.
"""
from enum import Enum


# ============================================================================
# Environment
# ============================================================================

class Environment(str, Enum):
    """Deployment environment enumeration."""
    DEVELOPMENT = "dev"
    STAGING = "stg"
    PRODUCTION = "prod"


# ============================================================================
# User & Authentication
# ============================================================================

class OrgRole(str, Enum):
    """Organization membership role."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class TokenType(str, Enum):
    """JWT token type enumeration."""
    ACCESS = "access"
    REFRESH = "refresh"


# ============================================================================
# Access & Permissions
# ============================================================================

class AccessType(str, Enum):
    """Resource access type."""
    PUBLIC = "public"
    RESTRICTED = "restricted"


# ============================================================================
# Document & Knowledge
# ============================================================================

class IndexStatus(str, Enum):
    """Document indexing status."""
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class FileType(str, Enum):
    """Supported document file types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


# ============================================================================
# Provider & Model
# ============================================================================

class AuthType(str, Enum):
    """Provider authentication type."""
    API_KEY = "api_key"
    BEARER = "bearer"
    NONE = "none"


class ModelType(str, Enum):
    """AI model type."""
    CHAT = "chat"
    EMBEDDING = "embedding"


# ============================================================================
# Agent & MCP
# ============================================================================

class TransportType(str, Enum):
    """MCP server transport type."""
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"


class ComponentType(str, Enum):
    """UI component type."""
    PAGE = "page"
    WIDGET = "widget"
    ACTION = "action"


# ============================================================================
# Audit
# ============================================================================

class AuditAction(str, Enum):
    """Audit log action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_CHANGE = "permission_change"
