"""
Centralized constants for the CMS backend.
Error codes, success messages, cache prefixes, pagination defaults.
"""


class ErrorCode:
    """
    Error code constants.
    Convention: {DOMAIN}_{ACTION} — frontend maps to i18n.
    """
    # Auth
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_REVOKED = "AUTH_TOKEN_REVOKED"
    AUTH_NOT_AUTHENTICATED = "AUTH_NOT_AUTHENTICATED"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    AUTH_EMAIL_EXISTS = "AUTH_EMAIL_EXISTS"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
    AUTH_REFRESH_TOKEN_INVALID = "AUTH_REFRESH_TOKEN_INVALID"

    # Organization
    ORG_NOT_FOUND = "ORG_NOT_FOUND"
    ORG_SLUG_EXISTS = "ORG_SLUG_EXISTS"
    ORG_MEMBERSHIP_REQUIRED = "ORG_MEMBERSHIP_REQUIRED"
    ORG_MEMBERSHIP_EXISTS = "ORG_MEMBERSHIP_EXISTS"

    # Permission
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PERMISSION_NOT_FOUND = "PERMISSION_NOT_FOUND"

    # User
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_EMAIL_EXISTS = "USER_EMAIL_EXISTS"

    # Group
    GROUP_NOT_FOUND = "GROUP_NOT_FOUND"
    GROUP_NAME_EXISTS = "GROUP_NAME_EXISTS"

    # Agent
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_DISABLED = "AGENT_DISABLED"
    AGENT_CODENAME_EXISTS = "AGENT_CODENAME_EXISTS"

    # MCP
    MCP_NOT_FOUND = "MCP_NOT_FOUND"
    MCP_CODENAME_EXISTS = "MCP_CODENAME_EXISTS"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"

    # Provider
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    PROVIDER_KEY_EXHAUSTED = "PROVIDER_KEY_EXHAUSTED"
    PROVIDER_KEY_INVALID = "PROVIDER_KEY_INVALID"

    # Knowledge
    FOLDER_NOT_FOUND = "FOLDER_NOT_FOUND"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_UPLOAD_FAILED = "DOCUMENT_UPLOAD_FAILED"
    INDEX_JOB_FAILED = "INDEX_JOB_FAILED"

    # General
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"


class SuccessMessage:
    """Standard success messages."""
    CREATED = "Resource created successfully"
    UPDATED = "Resource updated successfully"
    DELETED = "Resource deleted successfully"
    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logout successful"


class CachePrefix:
    """Cache key prefix constants."""
    USER_PERMISSIONS = "perm"
    ORG_AGENTS = "org_agents"
    PROVIDER_KEYS = "prov_keys"
    USER_INFO = "user"
    ORG_CONFIG = "org_config"
    BLACKLIST = "blacklist"
    RATE_LIMIT = "ratelimit"


class Pagination:
    """Pagination defaults."""
    DEFAULT_PAGE = 1
    DEFAULT_SIZE = 20
    MAX_SIZE = 100


class FileConstants:
    """File upload constants."""
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
