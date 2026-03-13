# Sprint 4: Tenant APIs (User, Group, Agent, MCP, Permission)

**Duration**: 4-5 ngày  
**Goal**: Full tenant-scoped CRUD APIs, tenant routing middleware, org agent enable/disable

**Depends on**: Sprint 3

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> 1. **Router = thin layer** — KHÔNG viết schema, business logic, DB query trong router. Router chỉ inject deps + gọi service + return.
> 2. **TTL/config tập trung** — KHÔNG hardcode TTL, expire time. Dùng `settings.py` hoặc `constants.py`.
> 3. **Redis cache cho data ít thay đổi** — `CacheService.get_or_set()` cho list/get. `CacheInvalidation` khi create/update/delete.
> 4. **Cache invalidation cascading** — Xoá/sửa data → clear tất cả cache liên quan (org, user, permission, agent...).
> 5. **json.dumps(default=str)** — Redis chỉ lưu raw data, CacheService tự serialize.
> 6. **Schema riêng file** — Mỗi resource có file schema riêng trong `schemas/`.
> 7. **Invite-only** — KHÔNG có endpoint đăng ký. Token blacklist = Redis TTL.
> 8. **Frontend datetime** — Backend lưu UTC, frontend dùng `lib/datetime.ts` convert timezone.
> 9. **Service singleton** — `svc = Service()` export cuối file.
> 10. **Dependency injection** — `get_cache_service`, `get_db_session`, `get_redis` qua Depends.
>
> ### 🔴 Permission System (HOTFIX — vi phạm sẽ gây lỗi bảo mật)
> 11. **Org ID resolution** — `require_org_membership` reads org_id: **path param → `X-Org-Id` header → query param → `request.state.org_id`**.
> 12. **Superuser = full access** — `check_permission()` returns `(True, "superuser")`. `require_org_membership` bypass membership check.
> 13. **Frontend gửi `X-Org-Id`** — `api-client.ts` auto-attach header. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 14. **PermissionGate loading guard** — Check `isLoading` trước khi deny. Superuser bypass `hasPermission`.
>
> ### Cache keys cần dùng trong Sprint 4:
> | Service | Cache Key | TTL | Invalidation |
> |---------|-----------|-----|--------------|
> | `user_svc.list(org_id)` | `org_users:{org_id}` | `CACHE_USER_TTL` | on add/update/remove member |
> | `group_svc.list(org_id)` | `org_groups:{org_id}` | `CACHE_DEFAULT_TTL` | on create/update/delete group |
> | `group_svc` permission change | `perm:{org_id}:*` | — | clear ALL org permissions |
> | `tenant agent list` | `org_agents:{org_id}` | `CACHE_AGENT_TTL` | on enable/disable/CRUD |

---

## Tasks

### 4.1 Tenant Routing
- [x] `core/middleware.py` — TenantResolverMiddleware: *(đã có từ Sprint 3)*
  - Dev: extract `tenant_id` from path `/t/{tenant_id}/...`
  - Stg/Prod: extract slug from subdomain `{slug}.domain.com`
  - Set `request.state.org` (CmsOrganization object)
  - Return 404 `ORG_NOT_FOUND` if invalid

### 4.2 Tenant User Management
- [x] `schemas/user.py` — UserUpdate, UserResponse, UserListResponse
- [x] `services/tenant_user.py` — tenant_user_svc: list (cached `org_users:{org_id}`), get, update, remove
- [x] `api/v1/tenant/users.py` — GET list, GET detail, PUT update, DELETE remove

### 4.3 Tenant Group Management
- [x] `schemas/group.py` — GroupCreate, GroupUpdate, GroupResponse, PermissionAssign, GroupMemberAction
- [x] `services/tenant_group.py` — tenant_group_svc: list (cached `org_groups:{org_id}`), CRUD + assign/revoke permissions + add/remove member
- [x] `api/v1/tenant/groups.py` — CRUD + permission assignment + member management

### 4.4 Tenant Agent Management
- [x] `services/tenant_agent.py` — tenant_agent_svc: list (cached `org_agents:{org_id}`), CRUD, enable/disable system agent
- [x] `api/v1/tenant/agents.py` — Custom agent CRUD + system agent enable/disable

### 4.5 Tenant MCP + Tool Management
- [x] `services/tenant_mcp.py` — tenant_mcp_svc: list (cached `org_mcp:{org_id}`), server CRUD, tool CRUD
- [x] `api/v1/tenant/mcp_servers.py` — MCP server CRUD + tool CRUD

### 4.6 Tenant Permission Management
- [x] `services/tenant_permission.py` — tenant_perm_svc: list all permissions
- [x] `api/v1/tenant/permissions.py` — List all available permissions
- [x] POST `permissions/check` — *(đã có từ Sprint 3: `api/v1/permissions.py`)*
- [ ] Resource permission overrides (cms_resource_permission) — *deferred to Sprint 5*

### 4.7 Tenant Audit Logs
- [x] `services/tenant_audit.py` — tenant_audit_svc: list logs with filters + pagination
- [x] `api/v1/tenant/audit_logs.py` — GET with filters (action, resource_type, user_id)

### 4.8 Router Registration
- [x] `api/v1/router.py` — 6 tenant sub-routers under `/tenant` prefix
- [x] `cache/keys.py` — added `org_users`, `org_groups`
- [x] `cache/invalidation.py` — added `clear_org_users`, `clear_org_groups`

### 4.9 Provider API Cleanup (bonus)
- [x] Removed `POST /system/providers` (create) — providers are seed data
- [x] Removed `DELETE /system/providers/{id}` (delete)
- [x] Frontend: removed Create button, Delete action, ConfirmDialog, `ProviderCreateData`

---

## Definition of Done
- [x] Tenant routing works via middleware *(Sprint 3)*
- [x] Full CRUD cho users, groups, agents, MCP in org (28 endpoints)
- [x] System agent enable/disable per org
- [ ] Resource permission override (grant/deny specific agent to user/group) — *deferred*
- [x] Audit trail logs endpoint with filters
- [x] Cache read-through (`get_or_set()`) + cascading invalidation
- [x] All routers = thin delegation layer (Rule 1)
- [x] 67 routes load OK, TypeScript frontend compile OK

