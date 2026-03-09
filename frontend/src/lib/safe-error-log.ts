import { isAxiosError } from 'axios';

function redactSensitiveSegments(input: string): string {
  const withRedactedQuery = input.replace(
    /([?&][A-Za-z0-9_.-]*(?:token|authorization|api[_-]?key|password|secret|sig|signature)[A-Za-z0-9_.-]*=)([^&\s]+)/gi,
    '$1[redacted]',
  );

  const withRedactedAssignments = withRedactedQuery.replace(
    /((?:access_token|refresh_token|id_token|authorization|api[_-]?key|password|secret)\s*[=:]\s*)([^\s,;]+)/gi,
    '$1[redacted]',
  );

  return withRedactedAssignments.replace(/\bBearer\s+[A-Za-z0-9\-._~+/]+=*/gi, 'Bearer [redacted]');
}

function resolveEndpoint(rawUrl: string | undefined): string {
  if (!rawUrl) return 'unknown';
  return redactSensitiveSegments(rawUrl.split('?')[0] || 'unknown');
}

export function logClientError(label: string, error: unknown): void {
  if (isAxiosError(error)) {
    const status = error.response?.status ?? 'unknown';
    const code = redactSensitiveSegments(error.code ?? 'unknown');
    const method = (error.config?.method ?? 'unknown').toUpperCase();
    const endpoint = resolveEndpoint(error.config?.url);
    const baseURL = typeof error.config?.baseURL === 'string' ? error.config.baseURL : '';
    const networkHint =
      (code === 'ECONNABORTED' || code === 'ERR_NETWORK') && typeof window !== 'undefined'
        ? ` — 後端可能未啟動，請確認 API 在 ${baseURL || 'http://localhost:8000/api'} 可連線`
        : '';
    console.error(
      `[${label}] request_failed status=${status} code=${code} method=${method} endpoint=${endpoint}${networkHint}`,
    );
    return;
  }

  let message: string;
  if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === 'object' && error !== null && 'type' in error && (error as Event).target !== undefined) {
    const ev = error as Event;
    message = `Event type=${ev.type}`;
    if (ev.target && typeof (ev.target as WebSocket).readyState === 'number') {
      message += ` readyState=${(ev.target as WebSocket).readyState}`;
    }
  } else {
    message = String(error ?? 'unknown');
  }
  console.error(`[${label}] ${redactSensitiveSegments(message)}`);
}
