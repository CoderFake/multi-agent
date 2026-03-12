# Sprint F3: Tenant Pages — Users, Groups, Permissions

**Duration**: 3-4 ngày  
**Goal**: Org-scoped user/group management, permission assignment UI

**Depends on**: Sprint F2 (layout + DataTable + OrgContext)

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> **Backend rules:** Router thin, TTL tập trung (`settings.py`), Redis cache + invalidation cascading, invite-only, token blacklist = Redis TTL.
>
> **Frontend rules:**
> 1. **Datetime UTC** — Dùng `lib/datetime.ts`. Backend trả UTC. KHÔNG format trực tiếp `new Date()`.
> 2. **UI rendering theo permission** — Wrap tất cả sensitive UI bằng `PermissionGate`. Ẩn/hiện actions dựa trên `actions{}` từ `/permissions/me`.
> 3. **Multi-tenant routing** — Dev: `/t/{tenant_id}/`, Prod: subdomain.
> 4. **Invite-only** — User chỉ join qua invite. Group assignment UI cho admin, KHÔNG có self-register.
> 5. **i18n** — Tất cả text dùng translation keys.
> 6. **Permission thay đổi → invalidate cache** — Sau khi gán/thu hồi permission/group → backend clear `perm:{org}:{user}` cache (backend handles, frontend cần re-fetch).
> 7. **Code structure separation** — KHÔNG define inline. Phải tách đúng vị trí:
>    - `types/models.ts` — Entity types + Create/Update DTOs
>    - `lib/api/{domain}.ts` — API functions per domain (system, tenant, permissions)
>    - `hooks/use-{feature}.ts` — Data fetching hooks, import từ `lib/api/` + `types/`
>    - Pages (`.tsx`) — Thin: chỉ import types, API functions, hooks, components. KHÔNG define interface/type/api call inline.
> 8. **Component granularity** — Chia nhỏ component nhất có thể để tái sử dụng. KHÔNG lồng gộp nhiều concerns vào 1 component. Mỗi component chỉ làm 1 việc (Single Responsibility).
>
> ### 🔴 Permission System (HOTFIX — vi phạm gây lỗi bảo mật/UX)
> 9. **X-Org-Id header** — `api-client.ts` tự gửi `X-Org-Id` trên mọi request. KHÔNG truyền org_id qua query param. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 10. **Superuser bypass** — `PermissionGate` bypass `hasPermission` cho superuser. Backend `check_permission()` return `(True, "superuser")`.
> 11. **PermissionGate loading guard** — Check `isLoading` TRƯỚC khi deny. Nếu không sẽ flash "Access Denied" khi vừa mount.
> 12. **fetchUIPermissions()** — KHÔNG truyền tham số. Org context gửi qua header tự động.

---

## Tasks

### F3.1 Org Detail Page
- [ ] `organizations/[orgId]/page.tsx`:
  - Org info card: name, slug, timezone, member count
  - Quick links → sub-pages (users, groups, agents...)
  - Stats: active users, total agents, total documents
- [ ] Nested layout `organizations/[orgId]/layout.tsx`:
  - Tab navigation hoặc secondary sidebar
  - Inject `orgId` from route params → OrgContext

### F3.2 User Management
- [ ] `organizations/[orgId]/users/page.tsx`:
  - DataTable: full_name, email, org_role, is_active, joined_at
  - **Invite user** dialog: email + org_role selection
  - **Edit member** dialog: change org_role (owner/admin/member)
  - **Remove member** confirm dialog
  - Status filter: active/inactive
  - Search by name/email
- [ ] API integration:
  - GET `/t/{orgId}/users` (list)
  - POST `/t/{orgId}/users` (invite)
  - PUT `/t/{orgId}/users/{userId}` (update role)
  - DELETE `/t/{orgId}/users/{userId}` (remove)

### F3.3 Group Management
- [ ] `organizations/[orgId]/groups/page.tsx`:
  - DataTable: name, description, is_system_default, member_count, permission_count
  - **Create group** dialog: name, description
  - **Edit group** dialog
  - **Delete group** confirm (chỉ non-system groups)
- [ ] Group detail — click row hoặc sub-page:
  - Members tab: list users in group + add/remove
  - Permissions tab: list assigned permissions + add/remove
  - Assign permission dialog: multi-select from available permissions
- [ ] API integration:
  - CRUD `/t/{orgId}/groups`
  - POST/DELETE `/t/{orgId}/groups/{id}/permissions`
  - POST/DELETE `/t/{orgId}/groups/{id}/members`

### F3.4 Permission Management
- [ ] `organizations/[orgId]/permissions/page.tsx`:
  - **Permission list**: grouped by content_type (app_label.model)
  - **User permission overrides**: DataTable of direct user→permission grants
  - **Resource permissions**: DataTable of resource-level overrides
  - **Create override** dialog: select user/group + permission + grant/deny
- [ ] **Permission check tool**: form to test "can user X do Y on Z?"
  - POST `/t/{orgId}/permissions/check`
  - Display result: granted/denied + reason
- [ ] API integration:
  - GET `/t/{orgId}/permissions` (list all)
  - CRUD `/t/{orgId}/permissions/resource` (resource overrides)
  - POST `/t/{orgId}/permissions/check`

### F3.5 PermissionGate Component
- [ ] `src/components/shared/permission-gate.tsx`:
  - `<PermissionGate permission="agent.view">...</PermissionGate>`
  - Conditionally renders children based on current user permissions
  - Fallback prop for "no access" message
- [ ] Apply to sidebar items: hide nav items user cannot access
- [ ] Apply to page-level: show "access denied" if no permission

---

## Definition of Done
- [ ] User list renders with invite/edit/remove flows
- [ ] Group CRUD with permission & member assignment
- [ ] Permission overrides: user-level + resource-level
- [ ] Permission check tool working
- [ ] PermissionGate hides/shows UI elements correctly
- [ ] All flows work with i18n (en/vi)
