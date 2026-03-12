"""
Custom types used across the CMS backend.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CurrentUser:
    """
    Represents the authenticated user context.
    Populated from JWT token + org membership lookup.
    Used as dependency injection in route handlers.
    """
    user_id: str
    email: str
    is_superuser: bool = False
    org_id: Optional[str] = None
    org_role: Optional[str] = None  # OrgRole value
    groups: list[str] = field(default_factory=list)
