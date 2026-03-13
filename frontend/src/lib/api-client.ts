/**
 * API client — fetch wrapper with credentials: 'include' for JWT cookies.
 * Automatically attaches X-Org-Id header when orgId is set.
 * Auto-refreshes access token on 401 and retries the failed request once.
 */

const API_BASE = process.env.NEXT_PUBLIC_CMS_API_URL || "http://localhost:8002/api/v1";

export interface ApiError {
  error_code: string;
  detail: string;
  status_code: number;
}

class ApiClient {
  private base: string;
  private orgId: string | null = null;
  private refreshing: Promise<void> | null = null;
  private expired = false; // prevent request spam after session expires

  constructor(base: string) {
    this.base = base;
  }

  /** Set the current org — all subsequent requests will carry X-Org-Id header */
  setOrgId(orgId: string | null) {
    this.orgId = orgId;
  }

  getOrgId(): string | null {
    return this.orgId;
  }

  /** Reset expired flag — call after successful login */
  resetExpired() {
    this.expired = false;
    this.refreshing = null;
  }

  private async request<T>(path: string, options: RequestInit = {}, retried = false): Promise<T> {
    // If session already expired, reject immediately (no network call)
    const skipAuthPaths = ["/auth/login", "/auth/refresh", "/auth/logout"];
    if (this.expired && !skipAuthPaths.some(p => path.startsWith(p))) {
      throw {
        error_code: "AUTH_TOKEN_EXPIRED",
        detail: "Session expired",
        status_code: 401,
      } as ApiError;
    }

    const url = `${this.base}${path}`;
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    // Only set JSON content type for non-FormData bodies
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = headers["Content-Type"] || "application/json";
    }

    // Attach org context for permission resolution
    if (this.orgId) {
      headers["X-Org-Id"] = this.orgId;
    }

    const res = await fetch(url, {
      ...options,
      credentials: "include",
      headers,
    });

    if (!res.ok) {
      // 401 on a non-auth-flow endpoint → try refresh then retry once
      if (res.status === 401 && !retried && !skipAuthPaths.some(p => path.startsWith(p))) {
        try {
          await this.refreshAccessToken();
          return this.request<T>(path, options, true);
        } catch {
          // refresh failed → already redirecting
          throw {
            error_code: "AUTH_TOKEN_EXPIRED",
            detail: "Session expired",
            status_code: 401,
          } as ApiError;
        }
      }

      const error: ApiError = await res.json().catch(() => ({
        error_code: "UNKNOWN_ERROR",
        detail: res.statusText,
        status_code: res.status,
      }));
      throw error;
    }

    return res.json();
  }

  /**
   * Refresh access token via HttpOnly cookie.
   * Deduplicates concurrent refresh calls using a shared promise.
   * Once expired, never attempts refresh again — all callers get immediate rejection.
   */
  private async refreshAccessToken(): Promise<void> {
    // Already expired → reject immediately, no network call
    if (this.expired) throw new Error("Session expired");

    // Dedup: reuse in-flight refresh promise
    if (this.refreshing) return this.refreshing;

    this.refreshing = (async () => {
      const res = await fetch(`${this.base}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        this.expired = true;
        // Keep this.refreshing as rejected promise — don't clear it
        // so all concurrent/future callers get immediate rejection
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        throw new Error("Refresh token expired");
      }
      // Only clear on success — allows fresh refresh on next 401
      this.refreshing = null;
    })();

    return this.refreshing;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  /** Post FormData (multipart) — browser auto-sets Content-Type with boundary. */
  postForm<T>(path: string, formData: FormData): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: formData,
    });
  }

  delete<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "DELETE",
      body: body ? JSON.stringify(body) : undefined,
    });
  }
}

export const api = new ApiClient(API_BASE);
