# Sprint F4: Tenant Pages — Agents, MCP, Providers

**Duration**: 3-4 ngày  
**Goal**: Agent config, MCP server + tool CRUD, provider key management

**Depends on**: Sprint F3 (org context + permission gate)

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> **Backend rules:** Router thin, TTL tập trung, Redis cache + invalidation, invite-only, token blacklist = Redis TTL.
>
> **Frontend rules:**
> 1. **Datetime UTC** — Dùng `lib/datetime.ts`. `last_used_at`, `cooldown_until` từ backend đều là UTC → format bằng `formatDateTime()`.
> 2. **UI rendering theo permission** — `PermissionGate` cho mọi CRUD action.
> 3. **Invite-only** — KHÔNG có form đăng ký.
> 4. **i18n** — Tất cả text dùng translation keys.
> 5. **JSON config** — Agent config, MCP connection_config, tool input_schema dùng JSON editor. Validate JSON trước submit.
> 6. **Provider key sensitivity** — Chỉ hiển thị last 4 chars. API key gửi lên encrypted bởi backend.
> 7. **Code structure separation** — KHÔNG define inline. `types/models.ts` cho entity types, `lib/api/{domain}.ts` cho API functions, `hooks/` cho data hooks. Pages chỉ import, KHÔNG define interface/type/api call inline.
> 8. **Component granularity** — Chia nhỏ component nhất có thể để tái sử dụng. KHÔNG lồng gộp nhiều concerns vào 1 component. Mỗi component chỉ làm 1 việc (Single Responsibility).
>
> ### 🔴 Permission System (HOTFIX — vi phạm gây lỗi bảo mật/UX)
> 9. **X-Org-Id header** — `api-client.ts` tự gửi `X-Org-Id` trên mọi request. KHÔNG truyền org_id qua query param. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 10. **Superuser bypass** — `PermissionGate` bypass `hasPermission` cho superuser. Backend `check_permission()` return `(True, "superuser")`.
> 11. **PermissionGate loading guard** — Check `isLoading` TRƯỚC khi deny. Nếu không sẽ flash "Access Denied" khi vừa mount.
> 12. **fetchUIPermissions()** — KHÔNG truyền tham số. Org context gửi qua header tự động.

---

## Tasks

### F4.1 Agent Management
- [ ] `organizations/[orgId]/agents/page.tsx`:
  - **System agents tab**: list system agents, toggle enable/disable per org
    - Switch component per agent row
    - Config override JSON editor (optional)
  - **Custom agents tab**: CRUD org-specific agents
    - DataTable: codename, display_name, is_active, provider, model
    - Create agent dialog: codename, display_name, description, default_config (JSON)
    - Edit/Delete actions
- [ ] Agent detail view:
  - Agent info card
  - Linked MCP servers/tools
  - Provider/model configuration
  - Knowledge sources (folders/documents)
- [ ] API integration:
  - GET/POST `/t/{orgId}/agents`
  - PUT/DELETE `/t/{orgId}/agents/{id}`
  - GET/PUT `/t/{orgId}/agents/{id}/org-config` (org_agent enable/config)

### F4.2 MCP Server Management
- [ ] `organizations/[orgId]/mcp-servers/page.tsx`:
  - **System MCP tab**: list system MCP servers (read-only)
  - **Custom MCP tab**: CRUD org-specific MCP servers
    - DataTable: codename, display_name, transport (stdio/sse/streamable-http), is_active
    - Create dialog: codename, display_name, transport, connection_config (JSON editor)
    - Edit/Delete
  - **Tools sub-section** per MCP server:
    - List tools: codename, display_name, input_schema
    - Create/Edit tool dialog
    - Toggle tool active status
- [ ] API integration:
  - CRUD `/t/{orgId}/mcp-servers`
  - CRUD `/t/{orgId}/mcp-servers/{id}/tools`

### F4.3 Provider & Key Management
- [ ] `organizations/[orgId]/providers/page.tsx`:
  - **Providers list**: available providers (from system registry)
  - **Org API keys**: per provider, list of encrypted keys
    - DataTable: provider_name, key_preview (last 4 chars), priority, is_active, last_used_at, cooldown status
    - **Add key** dialog: select provider, paste API key, set priority
    - **Edit key** dialog: update priority, toggle active
    - **Delete key** confirm
    - Visual indicator: key in cooldown (rate-limited) vs available
  - **Agent ↔ Provider mapping**:
    - DataTable: agent, provider, model, is_active
    - Create mapping: select agent → provider → model
    - Edit/Delete mapping
- [ ] API integration:
  - GET `/t/{orgId}/providers` (list available)
  - CRUD `/t/{orgId}/providers/keys` (org API keys)
  - CRUD `/t/{orgId}/providers/agent-mapping` (agent↔provider↔model)

### F4.4 JSON Editor Component
- [ ] `src/components/forms/json-editor.tsx`:
  - Textarea with JSON validation
  - Formatted display + edit mode
  - Error highlighting for invalid JSON
  - Used in: agent config, MCP connection_config, tool input_schema

---

## Definition of Done
- [ ] System agents: toggle enable/disable per org
- [ ] Custom agents: full CRUD
- [ ] MCP servers + tools: full CRUD with JSON config editor
- [ ] Provider keys: add/edit/delete with priority, cooldown indicator
- [ ] Agent ↔ Provider ↔ Model mapping working
- [ ] All pages permission-gated
