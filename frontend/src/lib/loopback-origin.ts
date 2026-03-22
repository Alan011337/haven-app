const DEFAULT_LOCAL_API_URL = 'http://localhost:8000/api';

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function normalizeHostname(hostname: string): string {
  return hostname.replace(/^\[(.*)\]$/, '$1').toLowerCase();
}

function isLoopbackHostname(hostname: string): boolean {
  const normalized = normalizeHostname(hostname);
  return normalized === 'localhost' || normalized === '127.0.0.1' || normalized === '::1';
}

export function resolveLoopbackFriendlyUrl(
  raw: string | undefined,
  currentOrigin?: string,
  fallback = DEFAULT_LOCAL_API_URL,
): string {
  const trimmed = trimTrailingSlash((raw || fallback).trim());
  try {
    const resolved = new URL(trimmed, currentOrigin);
    if (currentOrigin) {
      const current = new URL(currentOrigin);
      if (
        isLoopbackHostname(resolved.hostname) &&
        isLoopbackHostname(current.hostname) &&
        normalizeHostname(resolved.hostname) !== normalizeHostname(current.hostname)
      ) {
        resolved.hostname = current.hostname;
      }
    }
    return trimTrailingSlash(resolved.toString());
  } catch {
    return trimmed;
  }
}

export function resolveLoopbackFriendlyApiUrl(raw?: string, currentOrigin?: string): string {
  return resolveLoopbackFriendlyUrl(raw, currentOrigin, DEFAULT_LOCAL_API_URL);
}

