const UUID_SEGMENT_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const LONG_ID_SEGMENT_RE = /^(?:\d{6,}|[0-9a-f]{16,})$/i;

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
