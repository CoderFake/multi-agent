/**
 * DateTime utilities — UTC ↔ local timezone serialization.
 *
 * Backend stores all dates as UTC. Frontend converts to user's local timezone
 * for display and converts back to UTC when sending to backend.
 *
 * Usage:
 *   import { formatDateTime, toLocalTime, toUTC } from '@/lib/datetime';
 *   const local = toLocalTime('2024-01-15T10:30:00Z', 'Asia/Ho_Chi_Minh');
 *   const utc   = toUTC(new Date());
 */

// ── Format constants ────────────────────────────────────────────────────

export const DATE_FORMAT = 'yyyy-MM-dd';
export const TIME_FORMAT = 'HH:mm:ss';
export const DATETIME_FORMAT = 'yyyy-MM-dd HH:mm:ss';
export const DATETIME_ISO = "yyyy-MM-dd'T'HH:mm:ss'Z'";

// ── UTC → Local ─────────────────────────────────────────────────────────

/**
 * Convert UTC date string to local timezone Date object.
 * @param utcStr - ISO 8601 UTC date string from backend
 * @param timezone - IANA timezone (e.g. 'Asia/Ho_Chi_Minh'), defaults to browser
 */
export function toLocalTime(utcStr: string, timezone?: string): Date {
  const date = new Date(utcStr);
  if (!timezone) return date;

  // Use Intl to format the date parts in the target timezone, then reconstruct
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  return new Date(formatter.format(date));
}

/**
 * Format a UTC date string for display in local timezone.
 * @param utcStr - ISO 8601 UTC date string from backend
 * @param timezone - IANA timezone, defaults to browser
 * @param options - Intl.DateTimeFormat options
 */
export function formatDateTime(
  utcStr: string | null | undefined,
  timezone?: string,
  options?: Intl.DateTimeFormatOptions,
): string {
  if (!utcStr) return '—';

  const date = new Date(utcStr);
  if (isNaN(date.getTime())) return '—';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    ...(timezone ? { timeZone: timezone } : {}),
    ...options,
  };

  return new Intl.DateTimeFormat('en-US', defaultOptions).format(date);
}

/**
 * Format date only (no time) for display.
 */
export function formatDate(utcStr: string | null | undefined, timezone?: string): string {
  return formatDateTime(utcStr, timezone, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * Format time only for display.
 */
export function formatTime(utcStr: string | null | undefined, timezone?: string): string {
  return formatDateTime(utcStr, timezone, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Format relative time (e.g. "3 hours ago", "in 2 days").
 */
export function formatRelativeTime(utcStr: string | null | undefined): string {
  if (!utcStr) return '—';

  const date = new Date(utcStr);
  if (isNaN(date.getTime())) return '—';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.abs(Math.floor(diffMs / 1000));
  const isPast = diffMs > 0;

  if (diffSeconds < 60) return isPast ? 'just now' : 'in a moment';

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    const label = diffMinutes === 1 ? 'minute' : 'minutes';
    return isPast ? `${diffMinutes} ${label} ago` : `in ${diffMinutes} ${label}`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    const label = diffHours === 1 ? 'hour' : 'hours';
    return isPast ? `${diffHours} ${label} ago` : `in ${diffHours} ${label}`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) {
    const label = diffDays === 1 ? 'day' : 'days';
    return isPast ? `${diffDays} ${label} ago` : `in ${diffDays} ${label}`;
  }

  const diffMonths = Math.floor(diffDays / 30);
  const label = diffMonths === 1 ? 'month' : 'months';
  return isPast ? `${diffMonths} ${label} ago` : `in ${diffMonths} ${label}`;
}

// ── Local → UTC ──────────────────────────────────────────────────────

/**
 * Convert a local Date to UTC ISO string for sending to backend.
 * Backend expects all dates in UTC.
 */
export function toUTC(localDate: Date): string {
  return localDate.toISOString();
}

/**
 * Get current time as UTC ISO string.
 */
export function nowUTC(): string {
  return new Date().toISOString();
}

/**
 * Parse a local datetime-local input value to UTC ISO string.
 * Used for form inputs: <input type="datetime-local" />
 */
export function localInputToUTC(localValue: string, timezone?: string): string {
  if (!timezone) {
    // Browser-local: the input value is already in local time
    const date = new Date(localValue);
    return date.toISOString();
  }

  // With timezone: we need to construct the date in that timezone
  // datetime-local format: "2024-01-15T10:30"
  const date = new Date(localValue);
  return date.toISOString();
}

/**
 * Check if a UTC date string is in the past.
 */
export function isExpired(utcStr: string): boolean {
  return new Date(utcStr).getTime() < Date.now();
}

/**
 * Check if a UTC date string is within N minutes from now.
 */
export function isExpiringSoon(utcStr: string, withinMinutes: number = 5): boolean {
  const expiresAt = new Date(utcStr).getTime();
  const threshold = Date.now() + withinMinutes * 60 * 1000;
  return expiresAt > Date.now() && expiresAt <= threshold;
}
