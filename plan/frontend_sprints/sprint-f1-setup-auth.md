# Sprint F1: Project Setup & Auth

**Duration**: 3-4 ngày
**Goal**: Init project, copy design system, i18n setup, JWT cookie auth, auth middleware

**Depends on**: Backend Sprint 2 (auth API)

> [!CAUTION]
> ## Quy tắc bắt buộc (áp dụng mọi sprint)
> **Backend rules (phải tuân thủ khi backend code liên quan):**
> 1. Router = thin layer — KHÔNG viết schema, business logic, DB query trong router.
> 2. TTL/config tập trung — KHÔNG hardcode. Dùng `settings.py`.
> 3. Redis cache cho data ít thay đổi — `CacheService.get_or_set()` + `CacheInvalidation`.
> 4. Invite-only — KHÔNG có endpoint/form đăng ký.
> 5. Token blacklist = Redis TTL — KHÔNG dùng DB table.
>
> **Frontend rules:**
> 6. **Datetime UTC** — Backend lưu UTC. Frontend dùng `lib/datetime.ts` (formatDateTime, toUTC, formatRelativeTime) convert timezone khi hiển thị, gửi UTC khi submit.
> 7. **UI rendering theo permission** — Sidebar, actions, pages render dựa trên `GET /permissions/me` response. Dùng `PermissionGate` component.
> 8. **Multi-tenant routing** — Dev: path `/t/{tenant_id}/`, Prod: subdomain `{slug}.domain.com`.
> 9. **Không self-register** — Chỉ login + accept-invite. KHÔNG có form đăng ký.
> 10. **i18n** — Tất cả text dùng translation keys, KHÔNG hardcode string. Default: en.
>
> ### 🔴 Permission System (HOTFIX — vi phạm gây lỗi bảo mật/UX)
> 11. **X-Org-Id header** — `api-client.ts` tự gửi `X-Org-Id` trên mọi request. KHÔNG truyền org_id qua query param. `OrgContext.switchOrg()` sync `api.setOrgId()`.
> 12. **Superuser bypass** — `PermissionGate` bypass `hasPermission` cho superuser. Backend `check_permission()` return `(True, "superuser")`.
> 13. **PermissionGate loading guard** — Check `isLoading` TRƯỚC khi deny. Nếu không sẽ flash "Access Denied" khi vừa mount.
> 14. **fetchUIPermissions()** — KHÔNG truyền tham số. Org context gửi qua header tự động.

---

## Architecture Notes

> **Invite-only** — không có form đăng ký. Admin mời user qua invite flow.
> **Token blacklist** = Redis TTL (`CacheKeys.blacklist(jti)`) — không dùng DB table.
> **UI components** sẽ được render theo permission group — backend trả `get_ui_permissions()` (Sprint 3).
> **Multi-tenant routing** — dev: path `/t/{tenant_id}/`, prod: subdomain `{slug}.domain.com` — Frontend F2.

---

## Tasks

### F1.1 Project Init
- [x] Init Next.js 16 tại `multi-agent/frontend/`
- [x] TypeScript, TailwindCSS 4, App Router, Turbopack, `src/` dir
- [x] Install dependencies: Radix UI, CVA, clsx, tailwind-merge, lucide-react, next-themes, SWR, react-hook-form, zod, next-intl, @tanstack/react-table, geist, motion, sonner

### F1.2 Design System
- [x] Copy globals.css (CMS-adapted: no chat-specific styles, added card/chart tokens)
- [x] Copy 16 UI primitives from `web/src/components/ui/`
- [x] Copy ThemeProvider, ThemeToggle, cn(), use-mobile

### F1.3 i18n Setup
- [x] `src/i18n/request.ts` — next-intl server config (locale from cookie)
- [x] `messages/en.json` + `messages/vi.json` — auth, errors (map error_codes), nav, dashboard
- [x] `next.config.mjs` — next-intl plugin
- [x] `LocaleSwitcher` component — en/vi dropdown, stores in cookie

### F1.4 Auth Core
- [x] `src/lib/api-client.ts` — fetch wrapper, `credentials: "include"` for JWT cookies
- [x] `src/lib/auth.ts` — login, logout, refreshToken, getMe
- [x] `src/types/auth.ts` — LoginRequest, MeResponse, OrgMembership
- [x] `src/types/api.ts` — PaginatedResponse, ErrorResponse
- [x] `src/contexts/auth-context.tsx` — AuthProvider (session check on mount, login/logout/refresh)
- [x] `src/middleware.ts` — redirect unauthenticated → /login, authenticated from /login → /dashboard

### F1.5 Auth Pages
- [x] `(auth)/layout.tsx` — centered layout, no sidebar
- [x] `(auth)/login/page.tsx` — email/password form, error mapping (error_code → i18n), ThemeToggle + LocaleSwitcher
- [x] `(dashboard)/layout.tsx` — wraps with AuthProvider
- [x] `(dashboard)/dashboard/page.tsx` — welcome + stats stub + superuser badge
- [ ] `(auth)/accept-invite/page.tsx` — nhận invite token → set password → auto-login (chờ InviteService backend Sprint 3)

### F1.6 Config & Types
- [x] `.env.local` — `NEXT_PUBLIC_CMS_API_URL=http://localhost:8002/api/v1`
- [x] Root `page.tsx` → redirect to `/dashboard`

---

## Notes for Later Sprints

- **Sprint F2**: Dashboard layout sẽ dùng `get_ui_permissions()` để render sidebar items theo permission. `OrgSwitcher` component cho multi-tenant.
- **Sprint F3**: `PermissionGate` component — conditionally render children theo permission codename. Invite user flow sẽ dùng `InviteService`.
- **Frontend tenant routing**: Dev mode API calls sẽ dùng path-based `/t/{orgId}/...`. `OrgContext` sẽ inject `orgId` vào tất cả API calls.

---

## Definition of Done
- [x] `npm run dev` compiles without errors
- [x] Login page renders đúng (en/vi, dark/light)
- [x] Login → dashboard flow hoạt động với backend (login → me → redirect)
- [x] Theme toggle + locale toggle hoạt động
- [x] Middleware redirect: unauthenticated → /login, authenticated /login → /dashboard
