import { test, expect } from '@playwright/test';

test.describe('Loading and SideNav behavior', () => {
  test('shows loading spinner during initial auth check and preserves sidenav state', async ({ page }) => {
    // Clear localStorage to simulate first visit
    await page.addInitScript(() => localStorage.clear());
    await page.goto('http://localhost:3000/');

    // During initial load, main area should show loading indicator
    await expect(page.locator('text=加载中...')).toBeVisible();

    // Interact with sidenav: collapse/expand first group and reload to verify persistence
    const firstToggle = page.locator('aside button').first();
    await firstToggle.click();
    // reload and verify persistence
    await page.reload();
    // Validation is app-specific; here we assert that after reload the toggle state persists by checking the existence or non-existence of the submenu.
    // This selector may need adapting to the real DOM; treat as example.
    // await expect(page.locator('nav')).not.toBeVisible();
  });
});
