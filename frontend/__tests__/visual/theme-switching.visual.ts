import { test, expect } from '@playwright/test';
import { 
  setupVisualTest, 
  navigateAndWait, 
  captureScreenshot, 
  hideDynamicElements,
  setTheme,
  testThemes,
  THEMES,
  LOCALES,
  VIEWPORTS
} from './visual-helpers';

/**
 * Theme Switching Visual Regression Tests
 * 
 * These tests ensure correct theme switching between:
 * - Light theme
 * - Dark theme
 * - Theme persistence
 * - Theme-specific component styling
 * - Color contrast and accessibility
 */

test.describe('Theme Switching - Dashboard', () => {
  test('Dashboard light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'dashboard-light-theme', {
      maxDiffPixels: 100,
      threshold: 0.3,
    });
  });

  test('Dashboard dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'dashboard-dark-theme', {
      maxDiffPixels: 100,
      threshold: 0.3,
    });
  });

  test('Dashboard theme toggle', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    // Capture light theme
    await captureScreenshot(page, 'dashboard-before-toggle');
    
    // Toggle to dark theme
    await setTheme(page, THEMES.DARK);
    await page.waitForTimeout(300);
    await captureScreenshot(page, 'dashboard-after-toggle-dark');
    
    // Toggle back to light theme
    await setTheme(page, THEMES.LIGHT);
    await page.waitForTimeout(300);
    await captureScreenshot(page, 'dashboard-after-toggle-light');
  });
});

test.describe('Theme Switching - Navigation', () => {
  test('Top navigation light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'topnav-light', {
      clip: await topBar.boundingBox(),
      maxDiffPixels: 30,
    });
  });

  test('Top navigation dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'topnav-dark', {
      clip: await topBar.boundingBox(),
      maxDiffPixels: 30,
    });
  });

  test('Side navigation light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-light', {
        clip: await sideNav.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });

  test('Side navigation dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-dark', {
        clip: await sideNav.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });
});

test.describe('Theme Switching - Cards', () => {
  test('Card light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const card = page.locator('.card, [class*="Card"]').first();
    if (await card.count() > 0) {
      await captureScreenshot(page, 'card-light', {
        clip: await card.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });

  test('Card dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const card = page.locator('.card, [class*="Card"]').first();
    if (await card.count() > 0) {
      await captureScreenshot(page, 'card-dark', {
        clip: await card.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });

  test('Card header light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const cardHeader = page.locator('.card-header, [class*="CardHeader"]').first();
    if (await cardHeader.count() > 0) {
      await captureScreenshot(page, 'card-header-light', {
        clip: await cardHeader.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Card header dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const cardHeader = page.locator('.card-header, [class*="CardHeader"]').first();
    if (await cardHeader.count() > 0) {
      await captureScreenshot(page, 'card-header-dark', {
        clip: await cardHeader.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });
});

test.describe('Theme Switching - Buttons', () => {
  test('Primary button light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const button = page.locator('button').first();
    if (await button.count() > 0) {
      await captureScreenshot(page, 'button-primary-light', {
        clip: await button.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Primary button dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const button = page.locator('button').first();
    if (await button.count() > 0) {
      await captureScreenshot(page, 'button-primary-dark', {
        clip: await button.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Secondary button light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const buttons = page.locator('button');
    if (await buttons.count() > 1) {
      const button = buttons.nth(1);
      await captureScreenshot(page, 'button-secondary-light', {
        clip: await button.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Secondary button dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const buttons = page.locator('button');
    if (await buttons.count() > 1) {
      const button = buttons.nth(1);
      await captureScreenshot(page, 'button-secondary-dark', {
        clip: await button.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});

test.describe('Theme Switching - Forms', () => {
  test('Input field light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/alerts');
    
    const input = page.locator('input[type="text"]').first();
    if (await input.count() > 0) {
      await captureScreenshot(page, 'input-light', {
        clip: await input.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Input field dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/alerts');
    
    const input = page.locator('input[type="text"]').first();
    if (await input.count() > 0) {
      await captureScreenshot(page, 'input-dark', {
        clip: await input.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Select dropdown light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/alerts');
    
    const select = page.locator('select').first();
    if (await select.count() > 0) {
      await captureScreenshot(page, 'select-light', {
        clip: await select.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Select dropdown dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/alerts');
    
    const select = page.locator('select').first();
    if (await select.count() > 0) {
      await captureScreenshot(page, 'select-dark', {
        clip: await select.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });
});

test.describe('Theme Switching - Tables', () => {
  test('Table light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/alerts');
    
    const table = page.locator('table').first();
    if (await table.count() > 0) {
      await captureScreenshot(page, 'table-light', {
        maxDiffPixels: 50,
      });
    }
  });

  test('Table dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/alerts');
    
    const table = page.locator('table').first();
    if (await table.count() > 0) {
      await captureScreenshot(page, 'table-dark', {
        maxDiffPixels: 50,
      });
    }
  });

  test('Table header light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/alerts');
    
    const tableHeader = page.locator('th').first();
    if (await tableHeader.count() > 0) {
      await captureScreenshot(page, 'table-header-light', {
        clip: await tableHeader.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Table header dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/alerts');
    
    const tableHeader = page.locator('th').first();
    if (await tableHeader.count() > 0) {
      await captureScreenshot(page, 'table-header-dark', {
        clip: await tableHeader.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });
});

test.describe('Theme Switching - Status Indicators', () => {
  test('Status badge light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const badge = page.locator('.badge, [class*="Badge"]').first();
    if (await badge.count() > 0) {
      await captureScreenshot(page, 'badge-light', {
        clip: await badge.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Status badge dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const badge = page.locator('.badge, [class*="Badge"]').first();
    if (await badge.count() > 0) {
      await captureScreenshot(page, 'badge-dark', {
        clip: await badge.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Progress bar light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const progress = page.locator('.progress, [class*="Progress"]').first();
    if (await progress.count() > 0) {
      await captureScreenshot(page, 'progress-light', {
        clip: await progress.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Progress bar dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const progress = page.locator('.progress, [class*="Progress"]').first();
    if (await progress.count() > 0) {
      await captureScreenshot(page, 'progress-dark', {
        clip: await progress.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });
});

test.describe('Theme Switching - Alerts Page', () => {
  test('Alerts page light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/alerts');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'alerts-light-theme', {
      maxDiffPixels: 100,
    });
  });

  test('Alerts page dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/alerts');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'alerts-dark-theme', {
      maxDiffPixels: 100,
    });
  });

  test('Alert item light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/alerts');
    
    const alertItem = page.locator('.alert-item, [class*="AlertItem"]').first();
    if (await alertItem.count() > 0) {
      await captureScreenshot(page, 'alert-item-light', {
        clip: await alertItem.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });

  test('Alert item dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/alerts');
    
    const alertItem = page.locator('.alert-item, [class*="AlertItem"]').first();
    if (await alertItem.count() > 0) {
      await captureScreenshot(page, 'alert-item-dark', {
        clip: await alertItem.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });
});

test.describe('Theme Switching - AI Copilot', () => {
  test('AI Copilot light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/ai-copilot');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'ai-copilot-light-theme', {
      maxDiffPixels: 100,
    });
  });

  test('AI Copilot dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/ai-copilot');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'ai-copilot-dark-theme', {
      maxDiffPixels: 100,
    });
  });

  test('Chat interface light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/ai-copilot');
    
    const chatContainer = page.locator('.chat, [class*="Chat"]').first();
    if (await chatContainer.count() > 0) {
      await captureScreenshot(page, 'chat-light', {
        clip: await chatContainer.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });

  test('Chat interface dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/ai-copilot');
    
    const chatContainer = page.locator('.chat, [class*="Chat"]').first();
    if (await chatContainer.count() > 0) {
      await captureScreenshot(page, 'chat-dark', {
        clip: await chatContainer.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });
});

test.describe('Theme Switching - Theme Persistence', () => {
  test('Theme persists after navigation', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    // Set to light theme
    await setTheme(page, THEMES.LIGHT);
    await page.waitForTimeout(300);
    
    // Navigate to another page
    await navigateAndWait(page, '/alerts');
    
    // Verify theme is still light
    const isLight = await page.evaluate(() => {
      return !document.documentElement.classList.contains('dark');
    });
    expect(isLight).toBe(true);
    
    await captureScreenshot(page, 'theme-persistence-light');
  });

  test('Theme persists after page reload', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    // Set to dark theme
    await setTheme(page, THEMES.DARK);
    await page.waitForTimeout(300);
    
    // Reload page
    await page.reload();
    await page.waitForTimeout(300);
    
    // Verify theme is still dark
    const isDark = await page.evaluate(() => {
      return document.documentElement.classList.contains('dark');
    });
    expect(isDark).toBe(true);
    
    await captureScreenshot(page, 'theme-persistence-dark');
  });
});

test.describe('Theme Switching - Color Contrast', () => {
  test('Text contrast in light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const text = page.locator('p, h1, h2, h3').first();
    await captureScreenshot(page, 'text-contrast-light', {
      clip: await text.boundingBox(),
      maxDiffPixels: 10,
    });
  });

  test('Text contrast in dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const text = page.locator('p, h1, h2, h3').first();
    await captureScreenshot(page, 'text-contrast-dark', {
      clip: await text.boundingBox(),
      maxDiffPixels: 10,
    });
  });

  test('Border contrast in light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const card = page.locator('.card, [class*="Card"]').first();
    if (await card.count() > 0) {
      await captureScreenshot(page, 'border-contrast-light', {
        clip: await card.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Border contrast in dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const card = page.locator('.card, [class*="Card"]').first();
    if (await card.count() > 0) {
      await captureScreenshot(page, 'border-contrast-dark', {
        clip: await card.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });
});

test.describe('Theme Switching - Theme Toggle Button', () => {
  test('Theme toggle button in light theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.LIGHT });
    await navigateAndWait(page, '/dashboard');
    
    const toggleButton = page.locator('button').filter({ hasText: /☾|☀/ }).first();
    if (await toggleButton.count() > 0) {
      await captureScreenshot(page, 'theme-toggle-light', {
        clip: await toggleButton.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Theme toggle button in dark theme', async ({ page }) => {
    await setupVisualTest(page, { theme: THEMES.DARK });
    await navigateAndWait(page, '/dashboard');
    
    const toggleButton = page.locator('button').filter({ hasText: /☾|☀/ }).first();
    if (await toggleButton.count() > 0) {
      await captureScreenshot(page, 'theme-toggle-dark', {
        clip: await toggleButton.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});
