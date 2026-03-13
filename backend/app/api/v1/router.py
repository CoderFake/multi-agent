"""
API v1 router — registers all sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.invites import router as invite_router
from app.api.v1.permissions import router as permission_router
from app.api.v1.system.organizations import router as org_router
from app.api.v1.system.agents import router as agent_router
from app.api.v1.system.providers import router as provider_router
from app.api.v1.system.mcp_servers import router as mcp_router
from app.api.v1.system.settings import router as settings_router
from app.api.v1.tenant.users import router as tenant_user_router
from app.api.v1.tenant.groups import router as tenant_group_router
from app.api.v1.tenant.agents import router as tenant_agent_router
from app.api.v1.tenant.mcp_servers import router as tenant_mcp_router
from app.api.v1.tenant.permissions import router as tenant_perm_router
from app.api.v1.tenant.audit_logs import router as tenant_audit_router
from app.api.v1.tenant.notifications import router as tenant_notification_router
from app.api.v1.tenant.feedback import router as feedback_router  # system-level, NOT tenant
from app.api.v1.tenant.agent_access import router as tenant_access_router
from app.api.v1.assets import router as assets_router

api_router = APIRouter()

# Auth endpoints (no prefix — auth.py already has prefix="/auth")
api_router.include_router(auth_router)

# Invite endpoints
api_router.include_router(invite_router)

# Permission endpoints (tenant scope — requires org_id in path/state)
api_router.include_router(permission_router)

# Feedback (system-level — any authenticated user can submit)
api_router.include_router(feedback_router)

# System CRUD endpoints (superuser only)
api_router.include_router(org_router, prefix="/system", tags=["system"])
api_router.include_router(agent_router, prefix="/system", tags=["system"])
api_router.include_router(provider_router, prefix="/system", tags=["system"])
api_router.include_router(mcp_router, prefix="/system", tags=["system"])
api_router.include_router(settings_router, prefix="/system", tags=["system"])

# Tenant CRUD endpoints (org membership required)
api_router.include_router(tenant_user_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_group_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_agent_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_mcp_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_perm_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_audit_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_notification_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(tenant_access_router, prefix="/tenant", tags=["tenant"])

# Asset serving (MinIO proxy)
api_router.include_router(assets_router, tags=["assets"])
