# Sprint 5: Provider Key Rotation + Knowledge Management

**Duration**: 4-5 ngày  
**Goal**: Provider system với key rotation, knowledge folder/document management, Milvus integration

**Depends on**: Sprint 4

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> 1. **Router = thin layer** — KHÔNG viết schema, business logic, DB query trong router.
> 2. **TTL/config tập trung** — KHÔNG hardcode TTL. Dùng `settings.py`. Ví dụ: `CACHE_PROVIDER_TTL`, `PROVIDER_KEY_COOLDOWN_SECONDS`.
> 3. **Redis cache** — `CacheService.get_or_set()` cho provider keys list, folder list, etc. `CacheInvalidation` khi mutation.
> 4. **Cache invalidation cascading** — Xoá provider key → clear `provider_keys:{org_id}:{provider_id}`. Xoá folder → clear folder cache + document cache.
> 5. **json.dumps(default=str)** — Redis chỉ lưu raw data.
> 6. **Schema riêng file** — `schemas/knowledge.py`, `schemas/provider.py` etc.
> 7. **Invite-only** — Token blacklist = Redis TTL.
> 8. **Frontend datetime** — Backend lưu UTC.
> 9. **Service singleton** — `provider_svc = ProviderService()`.
> 10. **Dependency injection** — `get_cache_service` qua Depends.
>
> ### 🔴 Permission System (HOTFIX — vi phạm sẽ gây lỗi bảo mật)
> 11. **Org ID resolution** — `require_org_membership` reads org_id: **path param → `X-Org-Id` header → query param → `request.state.org_id`**.
> 12. **Superuser = full access** — `check_permission()` returns `(True, "superuser")`. `require_org_membership` bypass membership check.
> 13. **Frontend gửi `X-Org-Id`** — `api-client.ts` auto-attach header. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 14. **PermissionGate loading guard** — Check `isLoading` trước khi deny. Superuser bypass `hasPermission`.
>
> ### Cache keys cần dùng trong Sprint 5:
> | Service | Cache Key | TTL | Invalidation |
> |---------|-----------|-----|--------------|
> | `provider_svc.get_keys(org, provider)` | `provider_keys:{org}:{provider}` | `CACHE_PROVIDER_TTL` | on add/rotate/cooldown/delete key |
> | `knowledge_svc.list_folders(org)` | `org_folders:{org}` | `CACHE_DEFAULT_TTL` | on create/update/delete folder |
> | `storage_svc` | — (no cache, stream) | — | — |

---

## Tasks

### 5.1 Provider Service (Key Rotation)
- [ ] `services/provider.py` — provider_svc:
  - `add_provider_key(org_id, provider_id, api_key) → encrypt + store`
  - `get_active_key(org_id, provider_id) → decrypt next available key (by priority, skip cooldown)`
  - `mark_key_cooldown(key_id, duration_seconds)` — khi gặp 429
  - `rotate_key(org_id, provider_id) → round-robin cycle`
  - Redis cache: provider_keys per org (TTL 5min)
- [ ] `api/v1/tenant/providers.py`:
  - CRUD provider keys (list, create, update, delete)
  - GET available providers (system + org custom)
  - CRUD agent↔provider↔model mapping (cms_agent_provider)
  - POST test-key — verify key works

### 5.2 Storage Service (MinIO)
- [ ] `services/storage.py` — storage_svc:
  - `upload_file(org_id, folder_path, file) → storage_path`
  - `download_file(storage_path) → bytes`
  - `delete_file(storage_path)`

### 5.3 Knowledge Folder Management
- [ ] `schemas/knowledge.py` — FolderCreate, FolderUpdate, FolderResponse, FolderTreeResponse
- [ ] `services/knowledge.py` — knowledge_svc:
  - Folder CRUD (nested tree, access_type: public/restricted)
  - Set folder access (cms_document_access — which groups can read/write)
- [ ] `api/v1/tenant/knowledge.py` — Folder endpoints

### 5.4 Knowledge Document Management
- [ ] `schemas/knowledge.py` ++ — DocumentUpload, DocumentResponse, DocumentListResponse
- [ ] `services/knowledge.py` ++:
  - Document upload (validate file type → MinIO → create DB record)
  - Document delete (remove from MinIO + Milvus + DB)
  - Set document access (inherit from folder or override)
  - Track index_status
- [ ] `api/v1/tenant/knowledge.py` ++ — Document endpoints

### 5.5 Milvus Integration & Indexing
- [ ] Milvus collection schema: `knowledge_{org_id}` (id, embedding, text, document_id, folder_id, agent_id, access_type, group_ids, file_name, chunk_index)
- [ ] `workers/indexing_worker.py`:
  - Consume from RabbitMQ queue
  - Load document → chunk → embed → insert Milvus
  - Store group_ids (comma-separated) and access_type per chunk
  - Update cms_knowledge_index_job + cms_document.index_status

### 5.6 Permission-filtered Search
- [ ] `services/knowledge.py` ++:
  - `search(org_id, user_id, agent_id, query, top_k) → filtered results`
  - Build Milvus expr: `agent_id == X AND (access_type == "public" OR group_ids like "%g1%" OR ...)`
  - Return ranked chunks
- [ ] `api/v1/tenant/knowledge.py` — POST knowledge/search

### 5.7 Agent Knowledge Sources
- [ ] CRUD `cms_agent_knowledge` — link agent ↔ folder/document as knowledge source
- [ ] `api/v1/tenant/knowledge.py` — agent-sources endpoints

---

## Definition of Done
- [ ] Provider key rotation: thêm 3 keys, gọi round-robin, key bị 429 → cooldown → dùng key khác
- [ ] Key exhausted → trả `PROVIDER_KEY_EXHAUSTED` error code
- [ ] Upload PDF → MinIO → index to Milvus → search returns chunks
- [ ] Public folder: mọi member search được
- [ ] Restricted folder: chỉ groups được gán mới search được
- [ ] Agent knowledge source: agent chỉ search trong assigned folders/docs
