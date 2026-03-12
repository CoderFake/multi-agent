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

api_router = APIRouter()

# Auth endpoints (no prefix — auth.py already has prefix="/auth")
api_router.include_router(auth_router)

# Invite endpoints
api_router.include_router(invite_router)

# Permission endpoints (tenant scope — requires org_id in path/state)
api_router.include_router(permission_router)

# System CRUD endpoints (superuser only)
api_router.include_router(org_router, prefix="/system", tags=["system"])
api_router.include_router(agent_router, prefix="/system", tags=["system"])
api_router.include_router(provider_router, prefix="/system", tags=["system"])
api_router.include_router(mcp_router, prefix="/system", tags=["system"])
api_router.include_router(settings_router, prefix="/system", tags=["system"])

# Sprint 4+: tenant scoped routers
# api_router.include_router(tenant_router, prefix="/t/{org_id}", tags=["Tenant"])
