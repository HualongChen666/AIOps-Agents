import { test, expect } from '@playwright/test';
import { 
  setupVisualTest, 
  navigateAndWait, 
  captureScreenshot, 
  hideDynamicElements,
  testViewport,
  testResponsiveViewports,
  VIEWPORTS,
  THEMES,
  LOCALES
} from './visual-helpers';

/**
 * Responsive Design Visual Regression Tests
 * 
 * These tests ensure the UI adapts correctly across:
 * - Mobile devices (375px - 414px)
 * - Tablets (768px - 1024px)
 * - Desktop screens (1024px - 1920px)
 * - Large desktop screens (1920px+)
 */

test.describe('Responsive - Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Dashboard on mobile viewport', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await testViewport(page, VIEWPORTS.MOBILE, 'dashboard-mobile-375x667');
  });

  test('Dashboard on mobile large viewport', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await testViewport(page, VIEWPORTS.MOBILE_LARGE, 'dashboard-mobile-414x896');
  });

  test('Dashboard on tablet viewport', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await testViewport(page, VIEWPORTS.TABLET, 'dashboard-tablet-768x1024');
  });

  test('Dashboard on desktop small viewport', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await testViewport(page, VIEWPORTS.DESKTOP_SMALL, 'dashboard-desktop-1024x768');
  });

  test('Dashboard on desktop viewport', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await testViewport(page, VIEWPORTS.DESKTOP, 'dashboard-desktop-1280x720');
  });

  test('Dashboard on desktop large viewport', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await testViewport(page, VIEWPORTS.DESKTOP_LARGE, 'dashboard-desktop-1920x1080');
  });

  test('Dashboard responsive navigation', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    // Test mobile navigation (hamburger menu)
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'dashboard-nav-mobile');
    
    // Test desktop navigation
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'dashboard-nav-desktop');
  });
});

test.describe('Responsive - Alerts Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Alerts page across all viewports', async ({ page }) => {
    await testResponsiveViewports(page, '/alerts', 'alerts');
  });

  test('Alerts table on mobile', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'alerts-table-mobile');
  });

  test('Alerts table on desktop', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'alerts-table-desktop');
  });

  test('Alerts filters on mobile', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const filters = page.locator('.filters, [class*="Filter"]').first();
    if (await filters.count() > 0) {
      await captureScreenshot(page, 'alerts-filters-mobile', {
        clip: await filters.boundingBox(),
      });
    }
  });

  test('Alerts filters on desktop', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const filters = page.locator('.filters, [class*="Filter"]').first();
    if (await filters.count() > 0) {
      await captureScreenshot(page, 'alerts-filters-desktop', {
        clip: await filters.boundingBox(),
      });
    }
  });
});

test.describe('Responsive - AI Copilot Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('AI Copilot across all viewports', async ({ page }) => {
    await testResponsiveViewports(page, '/ai-copilot', 'ai-copilot');
  });

  test('Chat interface on mobile', async ({ page }) => {
    await navigateAndWait(page, '/ai-copilot');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'ai-copilot-chat-mobile');
  });

  test('Chat interface on desktop', async ({ page }) => {
    await navigateAndWait(page, '/ai-copilot');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'ai-copilot-chat-desktop');
  });

  test('Chat input on mobile', async ({ page }) => {
    await navigateAndWait(page, '/ai-copilot');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const chatInput = page.locator('textarea, input[type="text"]').last();
    if (await chatInput.count() > 0) {
      await captureScreenshot(page, 'ai-copilot-input-mobile', {
        clip: await chatInput.boundingBox(),
      });
    }
  });
});

test.describe('Responsive - Navigation Components', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Side navigation on mobile', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-mobile', {
        clip: await sideNav.boundingBox(),
      });
    }
  });

  test('Side navigation on tablet', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.TABLET);
    await page.waitForTimeout(200);
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-tablet', {
        clip: await sideNav.boundingBox(),
      });
    }
  });

  test('Side navigation on desktop', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-desktop', {
        clip: await sideNav.boundingBox(),
      });
    }
  });

  test('Top bar on mobile', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'topbar-mobile', {
      clip: await topBar.boundingBox(),
    });
  });

  test('Top bar on desktop', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'topbar-desktop', {
      clip: await topBar.boundingBox(),
    });
  });
});

test.describe('Responsive - Cards and Grids', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Dashboard cards grid on mobile', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const grid = page.locator('.grid').first();
    await captureScreenshot(page, 'dashboard-grid-mobile', {
      clip: await grid.boundingBox(),
    });
  });

  test('Dashboard cards grid on tablet', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.TABLET);
    await page.waitForTimeout(200);
    
    const grid = page.locator('.grid').first();
    await captureScreenshot(page, 'dashboard-grid-tablet', {
      clip: await grid.boundingBox(),
    });
  });

  test('Dashboard cards grid on desktop', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const grid = page.locator('.grid').first();
    await captureScreenshot(page, 'dashboard-grid-desktop', {
      clip: await grid.boundingBox(),
    });
  });

  test('Dashboard cards grid on large desktop', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP_LARGE);
    await page.waitForTimeout(200);
    
    const grid = page.locator('.grid').first();
    await captureScreenshot(page, 'dashboard-grid-large-desktop', {
      clip: await grid.boundingBox(),
    });
  });
});

test.describe('Responsive - Forms', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Form layout on mobile', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const form = page.locator('form').first();
    if (await form.count() > 0) {
      await captureScreenshot(page, 'form-layout-mobile', {
        clip: await form.boundingBox(),
      });
    }
  });

  test('Form layout on desktop', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const form = page.locator('form').first();
    if (await form.count() > 0) {
      await captureScreenshot(page, 'form-layout-desktop', {
        clip: await form.boundingBox(),
      });
    }
  });

  test('Form inputs on mobile', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const input = page.locator('input').first();
    if (await input.count() > 0) {
      await captureScreenshot(page, 'form-input-mobile', {
        clip: await input.boundingBox(),
      });
    }
  });
});

test.describe('Responsive - Tables', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Table horizontal scroll on mobile', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const table = page.locator('table').first();
    if (await table.count() > 0) {
      await captureScreenshot(page, 'table-mobile');
    }
  });

  test('Table on desktop', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const table = page.locator('table').first();
    if (await table.count() > 0) {
      await captureScreenshot(page, 'table-desktop');
    }
  });
});

test.describe('Responsive - Charts', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Chart on mobile', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    
    const chart = page.locator('.chart, [class*="Chart"], canvas').first();
    if (await chart.count() > 0) {
      await captureScreenshot(page, 'chart-mobile', {
        clip: await chart.boundingBox(),
      });
    }
  });

  test('Chart on desktop', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    
    const chart = page.locator('.chart, [class*="Chart"], canvas').first();
    if (await chart.count() > 0) {
      await captureScreenshot(page, 'chart-desktop', {
        clip: await chart.boundingBox(),
      });
    }
  });
});

test.describe('Responsive - Breakpoints', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Breakpoint at 640px (sm)', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 640, height: 800 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'breakpoint-640px');
  });

  test('Breakpoint at 768px (md)', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 768, height: 800 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'breakpoint-768px');
  });

  test('Breakpoint at 1024px (lg)', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 1024, height: 800 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'breakpoint-1024px');
  });

  test('Breakpoint at 1280px (xl)', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'breakpoint-1280px');
  });

  test('Breakpoint at 1536px (2xl)', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 1536, height: 800 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'breakpoint-1536px');
  });
});

test.describe('Responsive - Orientation', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Mobile portrait orientation', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'mobile-portrait');
  });

  test('Mobile landscape orientation', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 667, height: 375 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'mobile-landscape');
  });

  test('Tablet portrait orientation', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'tablet-portrait');
  });

  test('Tablet landscape orientation', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'tablet-landscape');
  });
});
