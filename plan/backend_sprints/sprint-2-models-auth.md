# Sprint 2: Auth & RBAC Models + Migration

**Duration**: 3-4 ngày  
**Goal**: Tất cả 27 DB models, Alembic migration, JWT cookie auth (invite-only), seed data

**Depends on**: Sprint 1

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> 1. **Router = thin layer** — KHÔNG viết schema, business logic, DB query trong router.
> 2. **TTL/config tập trung** — KHÔNG hardcode TTL, expire time. Dùng `settings.py`.
> 3. **Redis cache cho data ít thay đổi** — `CacheService.get_or_set()` + `CacheInvalidation` khi mutation.
> 4. **Cache invalidation cascading** — Mutation nào phải clear cache liên quan (org, user, permission...).
> 5. **json.dumps(default=str)** — Redis chỉ lưu raw data.
> 6. **Schema riêng file** — KHÔNG inline schema trong router.
> 7. **Invite-only** — KHÔNG có endpoint đăng ký. Token blacklist = Redis TTL.
> 8. **Frontend datetime** — Backend lưu UTC, frontend convert timezone.
> 9. **Service singleton** — `svc = Service()` export cuối file.
> 10. **Dependency injection** — `get_cache_service`, `get_db_session`, `get_redis` qua Depends.
>
> ### 🔴 Permission System (HOTFIX — vi phạm sẽ gây lỗi bảo mật)
> 11. **Org ID resolution** — `require_org_membership` reads org_id: **path param → `X-Org-Id` header → query param → `request.state.org_id`**.
> 12. **Superuser = full access** — `check_permission()` returns `(True, "superuser")`. `require_org_membership` bypass membership check.
> 13. **Frontend gửi `X-Org-Id`** — `api-client.ts` auto-attach header. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 14. **PermissionGate loading guard** — Check `isLoading` trước khi deny. Superuser bypass `hasPermission`.

---

## Architecture Decisions

### Invite-Only Registration (không tự đăng ký)
- Không có endpoint `/register` — superuser/admin mời user qua invite flow
- `CmsInvite` model: admin tạo invite → email với token + temp password (lưu Redis TTL) → user confirm invite → tạo account auto
- Pattern: giống `embed_chatbot` project (`InviteService.create_invite()` → `confirm_invite()`)

### Token Blacklist = Redis TTL (không dùng DB table)
- **Không dùng `CmsBlacklist` table** — token blacklisting hoàn toàn qua Redis
- `CacheKeys.blacklist(jti)` → Redis SETEX với TTL = remaining token lifetime
- Khi token hết hạn → Redis tự xoá key → không cần cleanup job
- Áp dụng cho: logout, refresh rotation, invite confirmation, user deactivation

---

## Tasks

### 2.1 Auth & RBAC Models
- [x] `models/user.py` — CmsUser (UUID PK, email UK, hashed_password, is_superuser, TimestampMixin, SoftDeleteMixin) + CmsInvite (token, org_id, org_role, status, expires_at)
- [x] `models/permission.py` — CmsContentType + CmsPermission
- [x] `models/group.py` — CmsGroup + M2M tables + CmsUserPermission

### 2.2 Organization Models
- [x] `models/organization.py` — CmsOrganization + CmsOrgMembership

### 2.3 Agent & MCP Models
- [x] `models/agent.py`, `models/mcp.py`, `models/ui.py`, `models/resource_permission.py`

### 2.4 Provider Models
- [x] `models/provider.py` — CmsProvider + CmsProviderKey + CmsAgentModel + CmsAgentProvider

### 2.5 Knowledge Models
- [x] `models/folder.py` + `models/document.py` (4 tables)

### 2.6 Other Models
- [x] `models/oauth.py`, `models/audit.py`, `models/system_setting.py`, `models/__init__.py`

### 2.7 Migration
- [x] `initial_cms_schema` — 27 tables (no blacklist)
- [x] `replace_blacklist_with_invite` — drop blacklist, add cms_invite

### 2.8 Seed Data
- [x] `app/init_db.py` — 13 content_types, 52 permissions, 4 default groups, superuser

### 2.9 Auth Endpoints (invite-only, Redis blacklist)
- [x] `schemas/auth.py` — LoginRequest, MeResponse (no RegisterRequest)
- [x] `services/auth.py` — login, refresh (Redis blacklist), logout (Redis blacklist), get_me
- [x] `core/dependencies.py` — get_current_user (Redis blacklist check), require_superuser, require_org_membership
- [x] `api/v1/auth.py` — POST login, refresh, logout; GET me (4 endpoints, no register)
- [x] `cache/keys.py` — blacklist(jti), invite_password(token)

### 2.10 Invite Service (Sprint 3 chạy tiếp)
- [ ] `schemas/invite.py` — InviteCreate, InviteResponse
- [ ] `services/invite.py` — create_invite (gen token + temp password Redis), confirm_invite (create user + org membership), revoke, resend
- [ ] `api/v1/admin/invites.py` — POST create, GET list, PUT revoke/resend, POST confirm

---

## Definition of Done
- [x] Migration creates 27 tables (no blacklist table)
- [x] Seed data populates content_types + permissions + default groups
- [x] POST `/auth/login` returns JWT HttpOnly cookies
- [x] GET `/auth/me` returns user info from cookie
- [x] Logout blacklists token in Redis (not DB)
