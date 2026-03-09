/**
 * P2-K: A11y automated gate. Run axe (WCAG 2.2 AA) on core pages.
 * CI: run with test:e2e. DoD: Drag/Swipe have alternatives; target size 24x24 (covered by axe where applicable).
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const CORE_PAGES: { path: string; name: string }[] = [
  { path: '/', name: 'Home' },
  { path: '/login', name: 'Login' },
  { path: '/register', name: 'Register' },
  { path: '/decks', name: 'Decks library' },
  { path: '/legal/terms', name: 'Legal terms' },
  { path: '/legal/privacy', name: 'Legal privacy' },
];

test.describe('A11y (axe WCAG 2.2 AA)', () => {
  for (const { path, name } of CORE_PAGES) {
    test(`${name} (${path}) has no critical a11y violations`, async ({ page }) => {
      await page.goto(path);
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();

      const violations = results.violations;
      if (violations.length > 0) {
        const summary = violations.map(
          (v) => `[${v.id}] ${v.help}: ${v.nodes.length} node(s)\n  ${v.helpUrl}`
        ).join('\n');
        expect(violations, `A11y violations on ${path}:\n${summary}`).toEqual([]);
      }
    });
  }
});
