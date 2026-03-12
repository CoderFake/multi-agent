# Sprint 1: Project Foundation & Core Infrastructure

**Duration**: 3-4 ngày  
**Goal**: Setup project, core infra (DB, Redis, settings), base models, Alembic

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> 1. **Router = thin layer** — KHÔNG viết schema, business logic, DB query trong router. Router chỉ inject deps + gọi service + return.
> 2. **TTL/config tập trung** — KHÔNG hardcode TTL, expire time, password length. Dùng `settings.py` hoặc `constants.py`.
> 3. **Redis cache cho data ít thay đổi** — Dùng `CacheService.get_or_set()` cho list/get. `CacheInvalidation` khi create/update/delete.
> 4. **Cache invalidation cascading** — Xoá org → clear org_info + org_config + org_agents + all_permissions. Mutation nào phải clear cache liên quan.
> 5. **json.dumps(default=str)** — Redis chỉ lưu raw data, CacheService tự serialize.
> 6. **Schema riêng file** — Mỗi resource có file schema riêng trong `schemas/`. KHÔNG inline trong router.
> 7. **Invite-only** — KHÔNG có endpoint đăng ký. Token blacklist = Redis TTL, KHÔNG dùng DB table.
> 8. **Frontend datetime** — Backend lưu UTC, frontend dùng `lib/datetime.ts` convert timezone khi hiển thị, gửi UTC khi submit.
> 9. **Service singleton** — Mỗi service export singleton: `org_svc = OrganizationService()`.
> 10. **Dependency injection** — Dùng `get_cache_service`, `get_db_session`, `get_redis` qua FastAPI Depends.
>
> ### 🔴 Permission System (HOTFIX — vi phạm sẽ gây lỗi bảo mật)
> 11. **Org ID resolution** — `require_org_membership` reads org_id: **path param → `X-Org-Id` header → query param → `request.state.org_id`**.
> 12. **Superuser = full access** — `check_permission()` returns `(True, "superuser")`. `require_org_membership` bypass membership check.
> 13. **Frontend gửi `X-Org-Id`** — `api-client.ts` auto-attach header. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 14. **PermissionGate loading guard** — Check `isLoading` trước khi deny. Superuser bypass `hasPermission`.

---

## Tasks

### 1.1 Project Setup
- [x] Tạo `backend/` directory structure (theo SRS Section 4)
- [x] `pyproject.toml` — dependencies: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, redis, alembic, pydantic-settings, python-jose, passlib[bcrypt], cryptography
- [x] `main.py` (root) — uvicorn entrypoint
- [x] `app/main.py` — FastAPI app factory, lifespan (connect DB/Redis on startup)
- [x] `app/__init__.py`

### 1.2 Config
- [x] `app/config/settings.py` — pydantic_settings: CMS_DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, CORS_ORIGINS, ENVIRONMENT, ENCRYPTION_KEY, MINIO_*
- [x] Update `.env` — thêm REDIS_URL, JWT_SECRET_KEY, CMS_PORT, ENCRYPTION_KEY

### 1.3 Core
- [x] `app/core/database.py` — DatabaseManager + RedisManager (copy pattern từ embed_chatbot)
- [x] `app/core/security.py` — JWT encode/decode (HttpOnly cookie), bcrypt hash/verify, Fernet encrypt/decrypt
- [x] `app/core/exceptions.py` — CmsException(error_code, status_code, detail), global exception handler
- [x] `app/core/middleware.py` — TenantResolverMiddleware, RequestLoggingMiddleware, CORS
- [x] `app/core/dependencies.py` — get_db_session, get_redis (chỉ infra deps, auth deps ở sprint 2)

### 1.4 Common
- [x] `app/common/enums.py` — OrgRole, TokenType, AccessType, IndexStatus, AuthType, ModelType, ...
- [x] `app/common/constants.py` — ErrorCode, SuccessMessage, CachePrefix, Pagination, FileConstants
- [x] `app/common/types.py` — CurrentUser class

### 1.5 Utils
- [x] `app/utils/logging.py` — get_logger
- [x] `app/utils/datetime_utils.py` — now(), to_org_timezone()
- [x] `app/utils/encryption.py` — Fernet encrypt_value, decrypt_value
- [x] `app/utils/hasher.py` — hash_password, verify_password
- [x] `app/utils/request_utils.py` — get_client_ip

### 1.6 Cache Layer
- [x] `app/cache/keys.py` — CacheKeys static methods
- [x] `app/cache/service.py` — CacheService (get, set, delete, get_or_set read-through)
- [x] `app/cache/invalidation.py` — CacheInvalidation (stub methods)

### 1.7 Base Models
- [x] `app/models/base.py` — Base, TimestampMixin, SoftDeleteMixin (copy pattern embed_chatbot)

### 1.8 Alembic
- [x] `alembic.ini` + `alembic/env.py` — loads Base.metadata
- [x] Verify: `uv run alembic upgrade head` runs clean (empty migration)

### 1.9 Docker
- [x] Add Redis service to `docker-compose.yml`

---

## Definition of Done
- [x] `uv run python main.py` starts without error
- [x] Redis + Postgres connection verified
- [x] Alembic init works
- [x] All `__init__.py` files created
