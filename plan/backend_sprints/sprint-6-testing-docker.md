# Sprint 6: Testing, Polish & Docker

**Duration**: 2-3 ngày  
**Goal**: Test coverage, Dockerfile, docker-compose cập nhật, documentation

**Depends on**: Sprint 5

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> 1. **Router = thin layer** — KHÔNG viết schema, business logic, DB query trong router.
> 2. **TTL/config tập trung** — KHÔNG hardcode TTL. Dùng `settings.py`.
> 3. **Redis cache** — `CacheService.get_or_set()` + `CacheInvalidation`.
> 4. **Cache invalidation cascading** — Test phải verify: sau mutation → cache bị clear → next read lấy fresh data.
> 5. **json.dumps(default=str)** — Redis chỉ lưu raw data.
> 6. **Schema riêng file** — KHÔNG inline schema trong router.
> 7. **Invite-only** — KHÔNG có endpoint đăng ký. Token blacklist = Redis TTL.
> 8. **Frontend datetime** — Backend lưu UTC.
> 9. **Service singleton** — Export singleton cuối file.
> 10. **Dependency injection** — Dùng `get_cache_service` qua Depends.
>
> ### 🔴 Permission System (HOTFIX — vi phạm sẽ gây lỗi bảo mật)
> 11. **Org ID resolution** — `require_org_membership` reads org_id: **path param → `X-Org-Id` header → query param → `request.state.org_id`**.
> 12. **Superuser = full access** — `check_permission()` returns `(True, "superuser")`. `require_org_membership` bypass membership check.
> 13. **Frontend gửi `X-Org-Id`** — `api-client.ts` auto-attach header. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 14. **PermissionGate loading guard** — Check `isLoading` trước khi deny. Superuser bypass `hasPermission`.

---

## Tasks

### 6.1 Test Infrastructure
- [ ] `tests/conftest.py`:
  - Test PostgreSQL database (async)
  - Test Redis instance
  - AsyncClient fixture (httpx)
  - Seed fixtures: superuser, org, org members, groups, permissions

### 6.2 Auth Tests
- [ ] `tests/test_auth.py`:
  - Login → JWT cookie set
  - Invalid credentials → `AUTH_INVALID_CREDENTIALS`
  - Cookie-based access → success
  - Expired token → `AUTH_TOKEN_EXPIRED`
  - Refresh → new access token
  - Logout → cookie cleared

### 6.3 Permission Tests
- [ ] `tests/test_permissions.py`:
  - Superuser: granted in system scope, denied in tenant scope
  - User override: granted wins, denied wins
  - Group permission: member of group with permission → granted
  - No permission: denied  
  - Cache: second check hits Redis

### 6.4 Tenant Isolation Tests
- [ ] `tests/test_tenant_isolation.py`:
  - User in Org A → cannot access Org B data
  - Superuser → cannot access any tenant data
  - Cross-org agent access → denied
  - Cross-org document access → denied

### 6.5 Provider Rotation Tests
- [ ] `tests/test_provider_rotation.py`:
  - 3 keys → round-robin order by priority
  - Key 1 cooldown → skip to key 2
  - All keys cooldown → `PROVIDER_KEY_EXHAUSTED`
  - Cooldown expires → key available again

### 6.6 Knowledge Tests
- [ ] `tests/test_knowledge.py`:
  - Create folder (public) → all members search
  - Create folder (restricted, group A) → only group A search
  - Upload document → index → search returns chunks
  - Document inherits folder access
  - Document override → different access
  - Cross-org search → empty results

### 6.7 Docker & Deployment
- [ ] `backend/Dockerfile` — multi-stage build
- [ ] `backend/start.sh` — production startup (alembic upgrade head + uvicorn)
- [ ] Update `docker-compose.yml` — add backend + Redis services
- [ ] Verify full docker-compose up works

### 6.8 Documentation
- [ ] `backend/README.md` — setup instructions, env vars, API docs link
- [ ] Swagger/OpenAPI auto-generated docs verify

---

## Definition of Done
- [ ] All tests pass: `uv run pytest -v`
- [ ] `docker-compose up` starts all services
- [ ] Swagger docs accessible at `/docs`
- [ ] Error responses all use error_code format
- [ ] README.md complete
