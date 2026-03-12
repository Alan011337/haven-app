const UUID_SEGMENT_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const LONG_ID_SEGMENT_RE = /^(?:\d{6,}|[0-9a-f]{16,})$/i;
export const SLOW_API_PROXY_THRESHOLD_MS = 1_000;
export const MAX_INTERNAL_UPSTREAM_REDIRECTS = 2;
const INTERNAL_REDIRECT_STATUSES = new Set([307, 308]);

export function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

export function trimApiSuffix(value: string): string {
  return value.replace(/\/api\/?$/, '');
}

export function redactProxyPath(pathname: string): string {
  const safePath = pathname.trim() || '/';
  return safePath
    .split('/')
    .map((segment) => {
      if (!segment) return segment;
      if (UUID_SEGMENT_RE.test(segment) || LONG_ID_SEGMENT_RE.test(segment)) {
        return ':id';
      }
      return segment;
    })
    .join('/');
}

export function buildUpstreamUrl(base: URL, segments: string[], search: string): string {
  const cleanSegments = segments
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment));
  const basePath = trimTrailingSlash(base.pathname);
  const pathname = [basePath, ...cleanSegments].filter(Boolean).join('/');
  const url = new URL(base.toString());
  url.pathname = pathname.startsWith('/') ? pathname : `/${pathname}`;
  url.search = search;
  return url.toString();
}

export function shouldLogSlowProxy(
  kind: 'api' | 'health',
  status: number,
  durationMs: number,
): boolean {
  return kind === 'api' && status < 500 && durationMs >= SLOW_API_PROXY_THRESHOLD_MS;
}

export function resolveInternalUpstreamRedirectUrl({
  currentUpstreamUrl,
  location,
  status,
  targetBase,
}: {
  currentUpstreamUrl: string;
  location: string | null;
  status: number;
  targetBase: URL;
}): string | null {
  if (!location || !INTERNAL_REDIRECT_STATUSES.has(status)) {
    return null;
  }

  try {
    const resolved = new URL(location, currentUpstreamUrl);
    if (resolved.host !== targetBase.host) {
      return null;
    }

    const basePath = trimTrailingSlash(targetBase.pathname);
    if (
      basePath &&
      resolved.pathname !== basePath &&
      !resolved.pathname.startsWith(`${basePath}/`)
    ) {
      return null;
    }

    const normalized = new URL(targetBase.toString());
    normalized.pathname = resolved.pathname;
    normalized.search = resolved.search;
    normalized.hash = resolved.hash;
    return normalized.toString();
  } catch {
    return null;
  }
}
