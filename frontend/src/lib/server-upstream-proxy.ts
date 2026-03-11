import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { logServerError, redactSensitiveSegments } from '@/lib/safe-error-log';
import {
  buildUpstreamUrl,
  redactProxyPath,
  shouldLogSlowProxy,
  trimApiSuffix,
  trimTrailingSlash,
} from '@/lib/upstream-proxy-utils';

const HOP_BY_HOP_REQUEST_HEADERS = new Set([
  'connection',
  'content-length',
  'host',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

const HOP_BY_HOP_RESPONSE_HEADERS = new Set([
  'connection',
  'content-length',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

function resolveBaseTarget(raw: string | undefined, transform: (value: string) => string): URL | null {
  const trimmed = raw?.trim();
  if (!trimmed) return null;
  try {
    const parsed = new URL(transform(trimmed));
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function resolveApiProxyTarget(): URL | null {
  return resolveBaseTarget(process.env.API_PROXY_TARGET, trimTrailingSlash);
}

export function resolveHealthProxyTarget(): URL | null {
  return resolveBaseTarget(process.env.API_PROXY_TARGET, trimApiSuffix);
}

function requestSupportsBody(method: string): boolean {
  return !['GET', 'HEAD'].includes(method.toUpperCase());
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    const normalized = key.toLowerCase();
    if (HOP_BY_HOP_REQUEST_HEADERS.has(normalized)) {
      continue;
    }
    headers.set(key, value);
  }

  const host = request.headers.get('host');
  if (host) {
    headers.set('x-forwarded-host', host);
  }
  headers.set('x-forwarded-proto', request.nextUrl.protocol.replace(/:$/, '') || 'https');
  return headers;
}

function buildResponseHeaders(upstreamHeaders: Headers): Headers {
  const headers = new Headers();
  for (const [key, value] of upstreamHeaders.entries()) {
    if (HOP_BY_HOP_RESPONSE_HEADERS.has(key.toLowerCase())) {
      continue;
    }
    if (key.toLowerCase() === 'set-cookie') {
      continue;
    }
    headers.set(key, value);
  }

  const rawGetSetCookie = (upstreamHeaders as Headers & { getSetCookie?: () => string[] }).getSetCookie;
  if (typeof rawGetSetCookie === 'function') {
    for (const cookie of rawGetSetCookie.call(upstreamHeaders)) {
      headers.append('set-cookie', cookie);
    }
  } else {
    const cookieHeader = upstreamHeaders.get('set-cookie');
    if (cookieHeader) {
      headers.append('set-cookie', cookieHeader);
    }
  }

  return headers;
}

function resolveRequestId(request: NextRequest): string {
  return request.headers.get('x-request-id')?.trim() || crypto.randomUUID();
}

function buildApiProxyFailureResponse(requestId: string): NextResponse {
  return NextResponse.json(
    {
      data: null,
      meta: { request_id: requestId },
      error: {
        code: 'upstream_proxy_error',
        message: 'Upstream unavailable',
        details: 'Upstream unavailable',
      },
      detail: 'Upstream unavailable',
    },
    { status: 502, headers: { 'x-request-id': requestId } },
  );
}

function buildHealthProxyFailureResponse(requestId: string): NextResponse {
  return NextResponse.json(
    {
      status: 'error',
      detail: 'Upstream unavailable',
      request_id: requestId,
    },
    { status: 502, headers: { 'x-request-id': requestId } },
  );
}

async function proxyRequest({
  kind,
  request,
  targetBase,
  pathSegments,
}: {
  kind: 'api' | 'health';
  request: NextRequest;
  targetBase: URL | null;
  pathSegments: string[];
}): Promise<NextResponse> {
  const requestId = resolveRequestId(request);
  const safePath = redactProxyPath(request.nextUrl.pathname);
  if (!targetBase) {
    logServerError('proxy-target-misconfigured', {
      kind,
      method: request.method,
      path: safePath,
      request_id: requestId,
    });
    return kind === 'api'
      ? buildApiProxyFailureResponse(requestId)
      : buildHealthProxyFailureResponse(requestId);
  }

  const upstreamUrl = buildUpstreamUrl(targetBase, pathSegments, request.nextUrl.search);
  const startedAtMs = Date.now();
  try {
    const body = requestSupportsBody(request.method) ? await request.arrayBuffer() : undefined;
    const upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: buildForwardHeaders(request),
      body,
      cache: 'no-store',
      redirect: 'manual',
    });

    const durationMs = Date.now() - startedAtMs;
    const upstreamRequestId = upstreamResponse.headers.get('x-request-id') || 'unknown';
    if (shouldLogSlowProxy(kind, upstreamResponse.status, durationMs)) {
      logServerError('proxy-upstream-slow', {
        kind,
        method: request.method,
        path: safePath,
        status: upstreamResponse.status,
        duration_ms: durationMs,
        upstream: redactSensitiveSegments(upstreamUrl.split('?')[0] || upstreamUrl),
        request_id: requestId,
        upstream_request_id: upstreamRequestId,
      });
    }
    if (upstreamResponse.status >= 500) {
      logServerError('proxy-upstream-http-error', {
        kind,
        method: request.method,
        path: safePath,
        status: upstreamResponse.status,
        duration_ms: durationMs,
        upstream: redactSensitiveSegments(upstreamUrl.split('?')[0] || upstreamUrl),
        request_id: requestId,
        upstream_request_id: upstreamRequestId,
      });
    }

    const headers = buildResponseHeaders(upstreamResponse.headers);
    headers.set('x-request-id', upstreamRequestId === 'unknown' ? requestId : upstreamRequestId);
    const payload = await upstreamResponse.arrayBuffer();
    return new NextResponse(payload, {
      status: upstreamResponse.status,
      headers,
    });
  } catch (error) {
    logServerError('proxy-upstream-transport-error', {
      kind,
      method: request.method,
      path: safePath,
      duration_ms: Date.now() - startedAtMs,
      upstream: redactSensitiveSegments(upstreamUrl.split('?')[0] || upstreamUrl),
      error:
        error instanceof Error
          ? redactSensitiveSegments(error.message)
          : redactSensitiveSegments(String(error)),
      request_id: requestId,
    });
    return kind === 'api'
      ? buildApiProxyFailureResponse(requestId)
      : buildHealthProxyFailureResponse(requestId);
  }
}

export async function proxyApiRequest(
  request: NextRequest,
  pathSegments: string[],
): Promise<NextResponse> {
  return proxyRequest({
    kind: 'api',
    request,
    targetBase: resolveApiProxyTarget(),
    pathSegments,
  });
}

export async function proxyHealthRequest(
  request: NextRequest,
  pathSegments: string[],
): Promise<NextResponse> {
  return proxyRequest({
    kind: 'health',
    request,
    targetBase: resolveHealthProxyTarget(),
    pathSegments: ['health', ...pathSegments],
  });
}
