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
- [ ] `core/middleware.py` — TenantResolverMiddleware:
  - Dev: extract `tenant_id` from path `/t/{tenant_id}/...`
  - Stg/Prod: extract slug from subdomain `{slug}.domain.com`
  - Set `request.state.org` (CmsOrganization object)
  - Return 404 `ORG_NOT_FOUND` if invalid

### 4.2 Tenant User Management
- [ ] `schemas/user.py` — UserCreate, UserUpdate, UserResponse, UserListResponse
- [ ] `services/user.py` — user_svc: CRUD within org, invite user, change role
- [ ] `api/v1/tenant/users.py` — CRUD (require `manage_user` permission)

### 4.3 Tenant Group Management
- [ ] `schemas/group.py` — GroupCreate, GroupUpdate, GroupResponse, PermissionAssign
- [ ] `services/group.py` — group_svc: CRUD + assign/revoke permissions to group
- [ ] `api/v1/tenant/groups.py` — CRUD + permission assignment endpoints

### 4.4 Tenant Agent Management
- [ ] `api/v1/tenant/agents.py`:
  - Custom agent CRUD (org_id = current org)
  - Enable/disable system agent (cms_org_agent)
  - List available agents (system enabled + custom)

### 4.5 Tenant MCP + Tool Management
- [ ] `api/v1/tenant/mcp_servers.py`:
  - Custom MCP server CRUD
  - Tool CRUD per MCP server

### 4.6 Tenant Permission Management
- [ ] `api/v1/tenant/permissions.py`:
  - List all available permissions
  - Resource permission overrides (cms_resource_permission)
  - POST `permissions/check` — check if current user has specific permission

### 4.7 Tenant Audit Logs
- [ ] `api/v1/tenant/audit_logs.py` — GET with filters (action, resource_type, date range)

### 4.8 Router Registration
- [ ] `api/v1/router.py` — Register tenant sub-routers with tenant prefix/middleware

---

## Definition of Done
- [ ] Dev routing: `localhost:8002/t/{org_id}/users` works
- [ ] Tenant isolation: user in Org X cannot see Org Y data
- [ ] Full CRUD cho users, groups, agents, MCP, permissions in org
- [ ] System agent enable/disable per org
- [ ] Resource permission override (grant/deny specific agent to user/group)
- [ ] Audit trail logs all tenant changes
