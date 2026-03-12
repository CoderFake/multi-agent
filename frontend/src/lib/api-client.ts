/**
 * API client — fetch wrapper with credentials: 'include' for JWT cookies.
 * Automatically attaches X-Org-Id header when orgId is set.
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

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.base}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

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
      const error: ApiError = await res.json().catch(() => ({
        error_code: "UNKNOWN_ERROR",
        detail: res.statusText,
        status_code: res.status,
      }));
      throw error;
    }

    return res.json();
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

  delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

export const api = new ApiClient(API_BASE);
