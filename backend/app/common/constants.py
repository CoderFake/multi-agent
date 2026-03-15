"""
Centralized constants for the CMS backend.
Error codes, success messages, cache prefixes, pagination defaults.
"""
from app.config.settings import settings
from app.common.enums import Environment

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


class CookieConstants:
    """Cookie constants."""
    COOKIE_SECURE = settings.ENVIRONMENT != Environment.DEVELOPMENT.value
    COOKIE_SAMESITE_ACCESS_TOKEN = "lax"
    COOKIE_SAMESITE_REFRESH_TOKEN = "strict"


class FeedbackConstants:
    """Feedback constants."""
    MAX_ATTACHMENTS = 5
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class FeedbackCategory:
    """Feedback category values — stored in DB."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    QUESTION = "question"
    OTHER = "other"

    ALL = {BUG, FEATURE_REQUEST, QUESTION, OTHER}


class FeedbackStatus:
    """Feedback status values — stored in DB."""
    NEW = "new"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"

    ALL = {NEW, REVIEWED, RESOLVED}


class InviteStatus:
    """Invite status values — stored in DB."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"

    ALL = {PENDING, ACCEPTED, EXPIRED, REVOKED}


class NotificationType:
    """Notification type values — stored in DB `type` column."""
    INVITE_ACCEPTED = "invite_accepted"
    ROLE_CHANGED = "role_changed"
    MEMBER_REMOVED = "member_removed"
    GROUP_ADDED = "group_added"
    GROUP_REMOVED = "group_removed"
    GROUP_DELETED = "group_deleted"
    PERMISSION_UPDATED = "permission_updated"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    FEEDBACK_RESOLVED = "feedback_resolved"

    ALL = {
        INVITE_ACCEPTED, ROLE_CHANGED, MEMBER_REMOVED,
        GROUP_ADDED, GROUP_REMOVED, GROUP_DELETED,
        PERMISSION_UPDATED, FEEDBACK_SUBMITTED, FEEDBACK_RESOLVED,
    }


class NotificationCode:
    """
    Notification i18n codes — frontend maps to locale strings.
    Convention: notification.{type} for title, notification.{type}_desc for message.
    Frontend usage: t(title_code, data)
    """
    # Invite
    INVITE_ACCEPTED = "notification.invite_accepted"
    INVITE_ACCEPTED_DESC = "notification.invite_accepted_desc"

    # Role
    ROLE_CHANGED = "notification.role_changed"
    ROLE_CHANGED_DESC = "notification.role_changed_desc"

    # Member
    MEMBER_REMOVED = "notification.member_removed"
    MEMBER_REMOVED_DESC = "notification.member_removed_desc"

    # Group
    GROUP_ADDED = "notification.group_added"
    GROUP_ADDED_DESC = "notification.group_added_desc"
    GROUP_REMOVED = "notification.group_removed"
    GROUP_REMOVED_DESC = "notification.group_removed_desc"
    GROUP_DELETED = "notification.group_deleted"
    GROUP_DELETED_DESC = "notification.group_deleted_desc"

    # Permission
    PERMISSION_UPDATED = "notification.permission_updated"
    PERMISSION_ASSIGNED_DESC = "notification.permission_assigned_desc"
    PERMISSION_REVOKED_DESC = "notification.permission_revoked_desc"

    # Feedback
    FEEDBACK_SUBMITTED = "notification.feedback_submitted"
    FEEDBACK_SUBMITTED_DESC = "notification.feedback_submitted_desc"
    FEEDBACK_RESOLVED = "notification.feedback_resolved"
    FEEDBACK_RESOLVED_DESC = "notification.feedback_resolved_desc"

class Timezone:
    """Supported timezone constants.

    Curated list of IANA timezones, grouped by region.
    Used by organization timezone selector.
    """

    ALL: list[dict[str, str]] = [
        # ── Asia ─────────────────────────────────────────────────────────
        {"value": "Asia/Ho_Chi_Minh", "label": "Asia/Ho Chi Minh (UTC+7)"},
        {"value": "Asia/Bangkok", "label": "Asia/Bangkok (UTC+7)"},
        {"value": "Asia/Jakarta", "label": "Asia/Jakarta (UTC+7)"},
        {"value": "Asia/Singapore", "label": "Asia/Singapore (UTC+8)"},
        {"value": "Asia/Kuala_Lumpur", "label": "Asia/Kuala Lumpur (UTC+8)"},
        {"value": "Asia/Manila", "label": "Asia/Manila (UTC+8)"},
        {"value": "Asia/Shanghai", "label": "Asia/Shanghai (UTC+8)"},
        {"value": "Asia/Hong_Kong", "label": "Asia/Hong Kong (UTC+8)"},
        {"value": "Asia/Taipei", "label": "Asia/Taipei (UTC+8)"},
        {"value": "Asia/Seoul", "label": "Asia/Seoul (UTC+9)"},
        {"value": "Asia/Tokyo", "label": "Asia/Tokyo (UTC+9)"},
        {"value": "Asia/Kolkata", "label": "Asia/Kolkata (UTC+5:30)"},
        {"value": "Asia/Dubai", "label": "Asia/Dubai (UTC+4)"},
        {"value": "Asia/Riyadh", "label": "Asia/Riyadh (UTC+3)"},
        # ── Europe ───────────────────────────────────────────────────────
        {"value": "Europe/London", "label": "Europe/London (UTC+0)"},
        {"value": "Europe/Paris", "label": "Europe/Paris (UTC+1)"},
        {"value": "Europe/Berlin", "label": "Europe/Berlin (UTC+1)"},
        {"value": "Europe/Madrid", "label": "Europe/Madrid (UTC+1)"},
        {"value": "Europe/Rome", "label": "Europe/Rome (UTC+1)"},
        {"value": "Europe/Amsterdam", "label": "Europe/Amsterdam (UTC+1)"},
        {"value": "Europe/Moscow", "label": "Europe/Moscow (UTC+3)"},
        {"value": "Europe/Istanbul", "label": "Europe/Istanbul (UTC+3)"},
        # ── Americas ─────────────────────────────────────────────────────
        {"value": "America/New_York", "label": "America/New York (UTC-5)"},
        {"value": "America/Chicago", "label": "America/Chicago (UTC-6)"},
        {"value": "America/Denver", "label": "America/Denver (UTC-7)"},
        {"value": "America/Los_Angeles", "label": "America/Los Angeles (UTC-8)"},
        {"value": "America/Toronto", "label": "America/Toronto (UTC-5)"},
        {"value": "America/Sao_Paulo", "label": "America/São Paulo (UTC-3)"},
        {"value": "America/Mexico_City", "label": "America/Mexico City (UTC-6)"},
        # ── Pacific ──────────────────────────────────────────────────────
        {"value": "Pacific/Auckland", "label": "Pacific/Auckland (UTC+12)"},
        {"value": "Australia/Sydney", "label": "Australia/Sydney (UTC+10)"},
        {"value": "Australia/Melbourne", "label": "Australia/Melbourne (UTC+10)"},
        # ── Africa ───────────────────────────────────────────────────────
        {"value": "Africa/Lagos", "label": "Africa/Lagos (UTC+1)"},
        {"value": "Africa/Cairo", "label": "Africa/Cairo (UTC+2)"},
        {"value": "Africa/Johannesburg", "label": "Africa/Johannesburg (UTC+2)"},
        # ── Other ────────────────────────────────────────────────────────
        {"value": "UTC", "label": "UTC (UTC+0)"},
    ]

    VALUES: list[str] = [tz["value"] for tz in ALL]


ROLE_HIERARCHY = {
    "member": 1,
    "admin": 2,
    "owner": 3,
}
