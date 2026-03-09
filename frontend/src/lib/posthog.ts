'use client';

import { logClientError } from '@/lib/safe-error-log';

type PosthogClient = {
  init: (apiKey: string, options?: Record<string, unknown>) => void;
  capture: (event: string, properties?: Record<string, unknown>) => void;
  identify: (distinctId: string, properties?: Record<string, unknown>) => void;
  reset: () => void;
  __loaded?: boolean;
};

declare global {
  interface Window {
    posthog?: PosthogClient;
  }
}

const DEFAULT_POSTHOG_SCRIPT_SRC = 'https://cdn.jsdelivr.net/npm/posthog-js@1.279.2/dist/module.no-external.js';
const DEFAULT_ALLOWED_POSTHOG_SCRIPT_HOSTS = new Set(['cdn.jsdelivr.net']);
const MAX_STRING_LEN = 160;
const PII_KEY_PATTERN = /(email|token|password|secret|authorization|cookie|content|journal|body_text|raw)/i;

let _bootstrapped = false;

function _sanitizeProps(props?: Record<string, unknown>): Record<string, unknown> {
  if (!props) return {};
  const sanitized: Record<string, unknown> = {};
  for (const [rawKey, rawValue] of Object.entries(props)) {
    const key = `${rawKey || ''}`.trim().toLowerCase();
    if (!key || PII_KEY_PATTERN.test(key)) continue;
    if (
      typeof rawValue === 'string'
      || typeof rawValue === 'number'
      || typeof rawValue === 'boolean'
      || rawValue === null
    ) {
      sanitized[key] = typeof rawValue === 'string' ? rawValue.slice(0, MAX_STRING_LEN) : rawValue;
    }
  }
  return sanitized;
}

function _resolvePosthogConfig(): { apiKey: string; host: string } | null {
  const apiKey = (process.env.NEXT_PUBLIC_POSTHOG_KEY || '').trim();
  const host = (process.env.NEXT_PUBLIC_POSTHOG_HOST || '').trim();
  if (!apiKey || !host) return null;
  return { apiKey, host };
}

function _resolvePosthogScriptConfig(): { src: string; integrity: string } | null {
  const rawSrc = (process.env.NEXT_PUBLIC_POSTHOG_SCRIPT_SRC || '').trim();
  const src = rawSrc || DEFAULT_POSTHOG_SCRIPT_SRC;
  const integrity = (process.env.NEXT_PUBLIC_POSTHOG_SCRIPT_INTEGRITY || '').trim();
  const allowUnpkg = ['1', 'true', 'yes', 'on'].includes(
    (process.env.NEXT_PUBLIC_POSTHOG_ALLOW_UNPKG || '').trim().toLowerCase(),
  );
  const requireIntegrity = ['1', 'true', 'yes', 'on'].includes(
    (process.env.NEXT_PUBLIC_POSTHOG_ENFORCE_INTEGRITY || '').trim().toLowerCase(),
  );
  const allowedHosts = new Set(DEFAULT_ALLOWED_POSTHOG_SCRIPT_HOSTS);
  if (allowUnpkg) {
    allowedHosts.add('unpkg.com');
  }
  try {
    const parsed = new URL(src);
    if (parsed.protocol !== 'https:' || !allowedHosts.has(parsed.host)) {
      return null;
    }
    if (requireIntegrity && !integrity) {
      return null;
    }
    return { src: parsed.toString(), integrity };
  } catch {
    return null;
  }
}

function _loadScript(scriptCfg: { src: string; integrity: string }): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined') {
      resolve();
      return;
    }
    if (window.posthog?.__loaded) {
      resolve();
      return;
    }

    const existing = document.querySelector<HTMLScriptElement>('script[data-haven-posthog="1"]');
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('posthog_script_load_failed')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = scriptCfg.src;
    script.async = true;
    script.defer = true;
    if (scriptCfg.integrity) {
      script.integrity = scriptCfg.integrity;
      script.crossOrigin = 'anonymous';
    }
    script.dataset.havenPosthog = '1';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('posthog_script_load_failed'));
    document.head.appendChild(script);
  });
}

export async function initPosthogClient(): Promise<void> {
  if (_bootstrapped || typeof window === 'undefined') return;
  const cfg = _resolvePosthogConfig();
  const scriptCfg = _resolvePosthogScriptConfig();
  if (!cfg) return;
  if (!scriptCfg) return;

  try {
    await _loadScript(scriptCfg);
    if (!window.posthog) {
      return;
    }
    window.posthog.init(cfg.apiKey, {
      api_host: cfg.host,
      capture_pageview: false,
      autocapture: false,
      person_profiles: 'identified_only',
      persistence: 'localStorage',
    });
    window.posthog.__loaded = true;
    _bootstrapped = true;
  } catch (error) {
    logClientError('posthog-init-failed', error);
  }
}

export function capturePosthogEvent(event: string, props?: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  if (!window.posthog?.capture) return;
  const normalized = (event || '').trim().toLowerCase();
  if (!normalized) return;
  try {
    window.posthog.capture(normalized, _sanitizeProps(props));
  } catch (error) {
    logClientError('posthog-capture-failed', error);
  }
}

export function identifyPosthogUser(userId: string, props?: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  if (!window.posthog?.identify) return;
  const normalized = (userId || '').trim();
  if (!normalized) return;
  try {
    window.posthog.identify(normalized, _sanitizeProps(props));
  } catch (error) {
    logClientError('posthog-identify-failed', error);
  }
}

export function resetPosthogUser(): void {
  if (typeof window === 'undefined') return;
  if (!window.posthog?.reset) return;
  try {
    window.posthog.reset();
  } catch (error) {
    logClientError('posthog-reset-failed', error);
  }
}
