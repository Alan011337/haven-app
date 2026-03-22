/**
 * DEG-01/DEG-02: Consume backend /health/degradation for UX banners and retry copy.
 * Backend root is API base without /api (e.g. http://localhost:8000).
 */
import { resolveLoopbackFriendlyApiUrl } from '@/lib/loopback-origin';

function getHealthBaseUrl(): string {
  if (typeof window === 'undefined') return '';
  const url = resolveLoopbackFriendlyApiUrl(process.env.NEXT_PUBLIC_API_URL, window.location.origin);
  return url.replace(/\/api\/?$/, '') || 'http://localhost:8000';
}

export type DegradationFeature = {
  fallback: string;
  severity: string;
};

export type DegradationStatus = {
  status: 'ok' | 'degraded' | 'unknown';
  features: Record<string, DegradationFeature>;
};

const DEFAULT: DegradationStatus = { status: 'ok', features: {} };

export async function fetchDegradationStatus(): Promise<DegradationStatus> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const base = getHealthBaseUrl();
    const response = await fetch(`${base}/health/degradation`, {
      method: 'GET',
      credentials: 'include',
      signal: controller.signal,
    });
    if (!response.ok) return DEFAULT;
    const data = (await response.json()) as DegradationStatus;
    if (data && typeof data.status === 'string') {
      return {
        status: data.status === 'degraded' ? 'degraded' : data.status === 'ok' ? 'ok' : 'unknown',
        features: typeof data.features === 'object' && data.features !== null ? data.features : {},
      };
    }
  } catch {
    // Network or parse error: assume ok to avoid blocking UX
  } finally {
    clearTimeout(timeout);
  }
  return DEFAULT;
}
