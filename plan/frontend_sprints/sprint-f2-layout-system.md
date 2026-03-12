# Sprint F2: Dashboard Layout & System Pages

**Duration**: 3-4 ngày  
**Goal**: Dashboard layout (sidebar + topbar), DataTable component, system admin CRUD pages

**Depends on**: Sprint F1 (auth + design system)

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> **Backend rules:** Router thin, TTL tập trung, Redis cache + invalidation, invite-only, token blacklist = Redis TTL.
>
> **Frontend rules:**
> 1. **Datetime UTC** — Dùng `lib/datetime.ts` (formatDateTime, toUTC). Backend trả UTC, frontend convert timezone khi hiển thị.
> 2. **UI rendering theo permission** — `GET /permissions/me` → `nav_items[]` + `actions{}`. Dùng `PermissionGate` wrap UI elements.
> 3. **Multi-tenant routing** — Dev: `/t/{tenant_id}/`, Prod: subdomain.
> 4. **Không self-register** — Chỉ login + accept-invite.
> 5. **i18n** — Tất cả text dùng translation keys.
> 6. **OrgSwitcher** — Chuyển org → re-fetch permissions → re-render sidebar + pages.
> 7. **API calls** — Gọi CMS backend (port 8002). KHÔNG chứa backend code trong frontend.
> 8. **Code structure separation** — KHÔNG define inline. Phải tách đúng vị trí:
>    - `types/models.ts` — Entity types + Create/Update DTOs
>    - `types/api.ts` — API response wrappers (PaginatedResponse, ErrorResponse)
>    - `lib/api/{domain}.ts` — API functions per domain (system, tenant, permissions)
>    - `hooks/use-{feature}.ts` — Data fetching hooks, import từ `lib/api/` + `types/`
>    - Pages (`.tsx`) — Thin: chỉ import types, API functions, hooks, components. KHÔNG define interface/type/api call inline.
> 9. **Component granularity** — Chia nhỏ component nhất có thể để tái sử dụng. KHÔNG lồng gộp nhiều concerns vào 1 component. Mỗi component chỉ làm 1 việc (Single Responsibility). VD: `DataTableToolbar`, `StatusBadge`, `ActionDropdown` phải là component riêng, không gộp vào page.
>
> ### 🔴 Permission System (HOTFIX — vi phạm gây lỗi bảo mật/UX)
> 10. **X-Org-Id header** — `api-client.ts` tự gửi `X-Org-Id` trên mọi request. KHÔNG truyền org_id qua query param. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 11. **Superuser bypass** — `PermissionGate` bypass `hasPermission` cho superuser. Backend `check_permission()` return `(True, "superuser")`.
> 12. **PermissionGate loading guard** — Check `isLoading` TRƯỚC khi deny. Nếu không sẽ flash "Access Denied" khi vừa mount.
> 13. **fetchUIPermissions()** — KHÔNG truyền tham số. Org context gửi qua header tự động.

---

## Tasks

### F2.1 Dashboard Layout
- [x] `(dashboard)/layout.tsx`:
  - `SidebarProvider` + `Sidebar` + `SidebarInset`
  - Top bar: `SidebarTrigger`, breadcrumb, `ThemeToggle`, `LocaleSwitcher`, `UserNav`
  - Responsive: sidebar collapsed on mobile (Sheet overlay)
- [x] `src/components/layout/app-sidebar.tsx`:
  - Logo/brand header
  - Navigation groups:
    - **System** (superuser only): Organizations, Agents, Providers, MCP Servers, Settings
    - **Current Org**: Users, Groups, Agents, MCP, Providers, Knowledge, Permissions, Audit
  - Active route highlighting
  - `OrgSwitcher` dropdown (danh sách orgs user thuộc)
  - Footer: user info + logout
- [x] `src/components/layout/top-bar.tsx` — breadcrumb + actions
- [x] `src/components/layout/user-nav.tsx` — dropdown: profile, org switch, logout
- [x] `src/components/layout/org-switcher.tsx`:
  - Select org from user memberships
  - Store selected org in context + cookie
  - All tenant API calls use this org_id

### F2.2 Org Context
- [x] `src/contexts/org-context.tsx`:
  - `OrgProvider` — load user memberships from `/auth/me`
  - `useCurrentOrg()` — current org, orgRole, switch org
  - Persist selected org in cookie/localStorage
- [x] `src/hooks/use-permissions.ts`:
  - `usePermissions()` — load permissions for current user in current org
  - `hasPermission(codename)` helper
  - `PermissionGate` component — show/hide children by permission

### F2.3 Shared Components
- [x] `src/components/shared/page-header.tsx` — title, description, breadcrumb, action buttons
- [x] `src/components/shared/empty-state.tsx` — icon + message + CTA button
- [x] `src/components/shared/status-badge.tsx` — active/inactive/pending color variants
- [x] `src/components/shared/confirm-dialog.tsx` — delete confirmation wrapper
- [x] `src/components/shared/search-input.tsx` — debounced search with icon
- [x] `src/components/shared/loading-skeleton.tsx` — page/table/card loading states

### F2.4 DataTable Component
- [x] `src/components/data-table/data-table.tsx`:
  - `@tanstack/react-table` integration
  - Column definitions, sorting, filtering
  - Pagination (server-side)
  - Row actions dropdown
  - Empty state
  - Loading skeleton
- [x] `src/components/data-table/data-table-toolbar.tsx` — search + filters + actions
- [x] `src/components/data-table/data-table-pagination.tsx` — page info + nav
- [x] `src/components/data-table/column-header.tsx` — sortable header

### F2.5 Dashboard Page
- [x] `(dashboard)/dashboard/page.tsx`:
  - Stats cards: total users, orgs, agents, active sessions
  - Quick actions
  - (Charts placeholder — Sprint F5)

### F2.6 System Pages (superuser only)
- [x] `(dashboard)/system/layout.tsx` — guard: redirect nếu không phải superuser
- [x] **Organizations** — `system/organizations/page.tsx`:
  - DataTable: name, slug, members count, status, created_at
  - Create org dialog (form: name, slug, timezone)
  - Edit/Delete actions
- [x] **System Agents** — `system/agents/page.tsx`:
  - DataTable: codename, display_name, is_active, created_at
  - Create/Edit agent dialog
  - Toggle active status
- [x] **System Providers** — `system/providers/page.tsx`:
  - DataTable: name, slug, auth_type, is_active
  - Create/Edit provider dialog
- [x] **System MCP Servers** — `system/mcp-servers/page.tsx`:
  - DataTable: codename, display_name, transport, is_active
  - Create/Edit + tools list
- [x] **System Settings** — `system/settings/page.tsx`:
  - Key-value list with edit inline
  - GET/PUT `/system/settings`

---

## Definition of Done
- [x] Sidebar renders with correct nav groups
- [x] OrgSwitcher loads user memberships and switches context
- [x] DataTable renders with sorting, pagination, search
- [x] All 5 system pages: list + create + edit + delete working
- [x] Theme toggle + locale toggle hoạt động trên dashboard
- [x] Mobile responsive (sidebar → sheet)
