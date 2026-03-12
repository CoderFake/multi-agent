# Sprint F5: Knowledge Base & Polish

**Duration**: 3-4 ngày  
**Goal**: Folder tree UI, document upload/index, audit logs, dashboard analytics, final polish

**Depends on**: Sprint F4

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> **Backend rules:** Router thin, TTL tập trung, Redis cache + invalidation, invite-only, token blacklist = Redis TTL.
>
> **Frontend rules:**
> 1. **Datetime UTC** — Dùng `lib/datetime.ts`. Audit log timestamps, document created_at đều UTC → `formatDateTime()` hoặc `formatRelativeTime()`.
> 2. **UI rendering theo permission** — `PermissionGate` cho mọi action (upload, delete, re-index).
> 3. **Invite-only** — KHÔNG có form đăng ký.
> 4. **i18n** — 100% coverage en + vi. Tất cả text dùng translation keys.
> 5. **File upload** — Validate file type + size trước khi gửi. Max size từ backend constants.
> 6. **Audit log** — Read-only, hiển thị old_values/new_values diff. KHÔNG cần cache (luôn fresh).
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

### F5.1 Knowledge Base — Folders
- [ ] `organizations/[orgId]/knowledge/page.tsx`:
  - **Folder tree** (left panel):
    - Hierarchical folder display (collapsible)
    - Create folder dialog: name, description, access_type (public/restricted)
    - Edit/Delete folder
    - Drag-and-drop reorder (sort_order) — optional
  - **Folder detail** (right panel):
    - Folder info: name, access_type, document count
    - Document list in folder
    - Access management: assign groups (for restricted folders)
- [ ] `src/components/knowledge/folder-tree.tsx`:
  - Recursive tree component
  - Expand/collapse with Collapsible
  - Context menu (right-click): rename, delete, create subfolder
  - Active folder highlighting

### F5.2 Knowledge Base — Documents
- [ ] Document list within folder:
  - DataTable: title, file_type, file_size, index_status, uploaded_by, created_at
  - Status badges: pending → indexing → indexed → failed
- [ ] **Upload document** dialog:
  - File input (accept: pdf, docx, txt, md)
  - File size validation (max from constants)
  - Title input
  - Upload progress bar
  - POST multipart to `/t/{orgId}/knowledge/documents`
- [ ] **Document detail** view:
  - File info card
  - Index status + chunk count
  - **Trigger re-index** button → POST `/t/{orgId}/knowledge/documents/{id}/index`
  - **Access management**: document-level group access override
  - Delete document confirm
- [ ] **Agent knowledge sources**:
  - Assign folders/documents to agents
  - UI: multi-select folders + documents per agent
  - POST/DELETE `/t/{orgId}/knowledge/agent-sources`

### F5.3 Audit Logs
- [ ] `organizations/[orgId]/audit-logs/page.tsx`:
  - DataTable (read-only): timestamp, user, action, resource_type, resource_id, ip_address
  - Filters: action type, user, date range, resource_type
  - Detail row: expand to show old_values / new_values diff
  - Export CSV — optional
- [ ] API: GET `/t/{orgId}/audit-logs` with query filters

### F5.4 Dashboard Analytics
- [ ] Upgrade `(dashboard)/dashboard/page.tsx`:
  - **Stats cards** (with motion animation):
    - Total organizations (superuser)
    - Total users in current org
    - Active agents
    - Documents indexed
    - Index jobs in progress
  - **Charts** (Recharts):
    - API usage over time (line chart)
    - Users per organization (bar chart)
    - Agent usage distribution (pie chart)
  - **Recent activity feed** — latest audit log entries

### F5.5 Profile Page
- [ ] `(dashboard)/profile/page.tsx`:
  - User info: name, email
  - Update password form
  - Organization memberships list
  - Theme preference
  - Locale preference

### F5.6 Final Polish
- [ ] Loading states: skeleton loaders for all pages
- [ ] Error boundaries: error.tsx + not-found.tsx for each route group
- [ ] Mobile responsive: verify all pages on mobile viewport
- [ ] i18n completeness: ensure all strings use translation keys
- [ ] Accessibility: keyboard navigation, aria-labels, focus management
- [ ] Performance: lazy load heavy pages (knowledge, audit logs)
- [ ] SEO: meta titles per page
- [ ] Favicon + app icon (reuse from web/)

---

## Definition of Done
- [ ] Folder tree: create/edit/delete, nested display
- [ ] Document upload + index trigger + status tracking
- [ ] Audit logs: filterable, expandable detail
- [ ] Dashboard: stats cards + charts
- [ ] Profile: update password, view memberships
- [ ] All pages: loading states, error boundaries, mobile responsive
- [ ] i18n: 100% coverage en + vi
