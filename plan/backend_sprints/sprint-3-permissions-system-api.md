# Backend Sprint 3 — Invite + Permission Engine + System CRUD

> **Status: COMPLETE** (refactored with Redis caching + code standards)

## Code Standards Applied
- ⚠️ **No schemas/business logic in routers** — routers are thin delegation layer
- ⚠️ **All TTLs in `settings.py`** — never hardcode cache TTL or invite expiry
- ⚠️ **CacheService.get_or_set()** for reads on rarely-changing data
- ⚠️ **CacheInvalidation** on ALL mutations (create/update/delete)
- ⚠️ **json.dumps(default=str)** — Redis stores raw data only; CacheService handles serialization

> [!CAUTION]
> ## 🔴 Permission System — Critical Rules (HOTFIX applied)
> 11. **Org ID resolution** — `require_org_membership` reads org_id in order: **path param → `X-Org-Id` header → query param → `request.state.org_id`**. KHÔNG chỉ dựa vào path param.
> 12. **Superuser = full access** — `check_permission()` returns `(True, "superuser")`. `require_org_membership` bypass membership check cho superuser. Frontend `PermissionGate` cũng bypass.
> 13. **Frontend gửi `X-Org-Id`** — `api-client.ts` auto-attach header. `OrgContext.switchOrg()` sync `api.setOrgId()`. KHÔNG truyền org_id qua query param.
> 14. **PermissionGate loading guard** — Phải check `isLoading` trước khi deny. Nếu không, flash "Access Denied" khi vừa mount.

---

## Task 3.1 — Schemas (7 files)
- [x] `schemas/invite.py` — InviteCreate, InviteConfirm, InviteResponse
- [x] `schemas/organization.py` — OrgCreate/Update/Response, MembershipResponse, AddMemberRequest
- [x] `schemas/permission.py` — PermCheckRequest/Response, UIPermissionsResponse
- [x] `schemas/agent.py` — AgentCreate/Update/Response
- [x] `schemas/mcp.py` — McpServerCreate/Update/Response, ToolCreate/Response
- [x] `schemas/provider.py` — ProviderCreate/Update/Response
- [x] `schemas/system_setting.py` — SettingResponse, SettingUpdate

## Task 3.2 — Services (8 files, all with CacheService)
| Service | Cache Key | TTL Setting | Invalidation |
|---------|-----------|-------------|--------------|
| `InviteService` | `invite_pwd:{token[:16]}` | `INVITE_EXPIRE_HOURS * 3600` | on confirm/revoke/resend |
| `PermissionService` | `perm:{org_id}:{user_id}` | `CACHE_PERMISSION_TTL` (300s) | on group/perm change |
| `AuditService` | — (write-only) | — | — |
| `OrganizationService` | `org:{org_id}` | `CACHE_ORG_TTL` (3600s) | on update/delete + cascading |
| `AgentService` | `sys:agents` | `CACHE_AGENT_TTL` (3600s) | on create/update/delete |
| `ProviderService` | `sys:providers` | `CACHE_PROVIDER_TTL` (7200s) | on create/update/delete |
| `McpService` | `sys:mcp_servers` | `CACHE_DEFAULT_TTL` (3600s) | on create/update/delete + tool |
| `SystemSettingService` | `sys:settings`, `sys:setting:{key}` | `CACHE_DEFAULT_TTL` | on upsert (single+list) |

## Task 3.3 — Cache Infrastructure
- [x] `cache/keys.py` — Added 6 system keys: `sys:agents`, `sys:providers`, `sys:mcp_servers`, `sys:settings`, `sys:setting:{key}`, `org:{org_id}`
- [x] `cache/invalidation.py` — Added 8 methods: `clear_system_agents/providers/mcp_servers/settings/setting`, `clear_org_info`, `clear_all_org_permissions`
- [x] `core/dependencies.py` — Added `get_cache_service()` dependency

## Task 3.4 — API Routers (7 files)
- [x] `api/v1/invites.py` — create, confirm (public), list, revoke, resend
- [x] `api/v1/permissions.py` — GET /permissions/me (UI), POST /permissions/check
- [x] `api/v1/system/organizations.py` — CRUD + members
- [x] `api/v1/system/agents.py` — CRUD system agents
- [x] `api/v1/system/providers.py` — CRUD system providers
- [x] `api/v1/system/mcp_servers.py` — CRUD + tools
- [x] `api/v1/system/settings.py` — GET/PUT key-value
- [x] `api/v1/router.py` — All sub-routers wired

## Task 3.5 — Settings
- [x] `config/settings.py` — Added `INVITE_EXPIRE_HOURS=72`, `INVITE_TEMP_PASSWORD_LENGTH=16`

---

## Cascading Invalidation Map
```
OrgService.delete(org_id) → clear_org_info(org_id)
                           → clear_org_config(org_id)
                           → clear_org_agents(org_id)
                           → clear_all_org_permissions(org_id)

OrgService.update(org_id) → clear_org_info(org_id)
                           → clear_org_config(org_id)

OrgService.add_member(user_id) → clear_user_info(user_id)

InviteService.confirm(token) → redis.delete(invite_pwd:{token})

PermissionService (group/perm change) → clear_user_permissions(user_id, org_id)
```

## Notes for Frontend Sprint F2
- Frontend calls `GET /permissions/me` with org_id → receives `nav_items[]` + `actions{}`
- Use `PermissionGate` component to wrap UI elements: `<PermissionGate action="agents.view">`
- Use `OrgSwitcher` to change org context → re-fetch permissions
- All datetime values from backend are UTC → use `frontend/src/lib/datetime.ts` for display
