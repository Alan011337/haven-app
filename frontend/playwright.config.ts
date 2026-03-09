import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';
const shouldStartLocalWebServer = !process.env.E2E_BASE_URL;
const webServerCommand =
  process.env.E2E_WEB_SERVER_COMMAND ??
  'NEXT_PUBLIC_API_URL=http://localhost:3000/api npm run dev -- --port 3000';
const parsedTimeoutMs = Number.parseInt(process.env.E2E_TEST_TIMEOUT_MS ?? '', 10);
const defaultTimeoutMs = process.env.CI ? 45_000 : 30_000;
const testTimeoutMs =
  Number.isFinite(parsedTimeoutMs) && parsedTimeoutMs > 0 ? parsedTimeoutMs : defaultTimeoutMs;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'dot' : 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  timeout: testTimeoutMs,
  webServer: shouldStartLocalWebServer
    ? {
        command: webServerCommand,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: process.env.CI ? 180_000 : 120_000,
      }
    : undefined,
});
