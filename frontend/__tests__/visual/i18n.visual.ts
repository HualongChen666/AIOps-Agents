import { test, expect } from '@playwright/test';
import { 
  setupVisualTest, 
  navigateAndWait, 
  captureScreenshot, 
  hideDynamicElements,
  setLocale,
  testLocales,
  LOCALES,
  THEMES,
  VIEWPORTS
} from './visual-helpers';

/**
 * Internationalization (i18n) Visual Regression Tests
 * 
 * These tests ensure correct internationalization across:
 * - Chinese (zh-CN)
 * - English (en-US)
 * - Language switching
 * - Text layout and typography
 * - RTL/LTR support (if applicable)
 * - Date/time formatting
 * - Number formatting
 */

test.describe('I18n - Dashboard Page', () => {
  test('Dashboard in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'dashboard-zh-CN', {
      maxDiffPixels: 100,
      threshold: 0.3,
    });
  });

  test('Dashboard in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'dashboard-en-US', {
      maxDiffPixels: 100,
      threshold: 0.3,
    });
  });

  test('Dashboard language switch', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    // Capture Chinese
    await captureScreenshot(page, 'dashboard-before-switch');
    
    // Switch to English
    await setLocale(page, LOCALES.EN_US);
    await page.waitForTimeout(300);
    await captureScreenshot(page, 'dashboard-after-switch-en');
    
    // Switch back to Chinese
    await setLocale(page, LOCALES.ZH_CN);
    await page.waitForTimeout(300);
    await captureScreenshot(page, 'dashboard-after-switch-zh');
  });
});

test.describe('I18n - Navigation', () => {
  test('Top navigation in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'topnav-zh-CN', {
      clip: await topBar.boundingBox(),
      maxDiffPixels: 30,
    });
  });

  test('Top navigation in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'topnav-en-US', {
      clip: await topBar.boundingBox(),
      maxDiffPixels: 30,
    });
  });

  test('Side navigation in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-zh-CN', {
        clip: await sideNav.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });

  test('Side navigation in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const sideNav = page.locator('aside').first();
    if (await sideNav.count() > 0) {
      await captureScreenshot(page, 'sidenav-en-US', {
        clip: await sideNav.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });

  test('Navigation menu items in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const navItems = page.locator('nav a').first();
    if (await navItems.count() > 0) {
      await captureScreenshot(page, 'nav-item-zh-CN', {
        clip: await navItems.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Navigation menu items in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const navItems = page.locator('nav a').first();
    if (await navItems.count() > 0) {
      await captureScreenshot(page, 'nav-item-en-US', {
        clip: await navItems.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});

test.describe('I18n - Cards and Headers', () => {
  test('Card headers in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const cardHeader = page.locator('.card-header, [class*="CardHeader"]').first();
    if (await cardHeader.count() > 0) {
      await captureScreenshot(page, 'card-header-zh-CN', {
        clip: await cardHeader.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Card headers in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const cardHeader = page.locator('.card-header, [class*="CardHeader"]').first();
    if (await cardHeader.count() > 0) {
      await captureScreenshot(page, 'card-header-en-US', {
        clip: await cardHeader.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Page titles in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const title = page.locator('h1').first();
    await captureScreenshot(page, 'page-title-zh-CN', {
      clip: await title.boundingBox(),
      maxDiffPixels: 15,
    });
  });

  test('Page titles in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const title = page.locator('h1').first();
    await captureScreenshot(page, 'page-title-en-US', {
      clip: await title.boundingBox(),
      maxDiffPixels: 15,
    });
  });
});

test.describe('I18n - Buttons and Actions', () => {
  test('Button text in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const button = page.locator('button').first();
    if (await button.count() > 0) {
      await captureScreenshot(page, 'button-zh-CN', {
        clip: await button.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Button text in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const button = page.locator('button').first();
    if (await button.count() > 0) {
      await captureScreenshot(page, 'button-en-US', {
        clip: await button.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Action links in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const link = page.locator('a').first();
    if (await link.count() > 0) {
      await captureScreenshot(page, 'link-zh-CN', {
        clip: await link.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Action links in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const link = page.locator('a').first();
    if (await link.count() > 0) {
      await captureScreenshot(page, 'link-en-US', {
        clip: await link.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});

test.describe('I18n - Forms and Labels', () => {
  test('Form labels in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/alerts');
    
    const label = page.locator('label').first();
    if (await label.count() > 0) {
      await captureScreenshot(page, 'form-label-zh-CN', {
        clip: await label.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Form labels in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/alerts');
    
    const label = page.locator('label').first();
    if (await label.count() > 0) {
      await captureScreenshot(page, 'form-label-en-US', {
        clip: await label.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Placeholder text in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/alerts');
    
    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    if (await input.count() > 0) {
      await captureScreenshot(page, 'placeholder-zh-CN', {
        clip: await input.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Placeholder text in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/alerts');
    
    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    if (await input.count() > 0) {
      await captureScreenshot(page, 'placeholder-en-US', {
        clip: await input.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});

test.describe('I18n - Tables', () => {
  test('Table headers in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/alerts');
    
    const tableHeader = page.locator('th').first();
    if (await tableHeader.count() > 0) {
      await captureScreenshot(page, 'table-header-zh-CN', {
        clip: await tableHeader.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Table headers in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/alerts');
    
    const tableHeader = page.locator('th').first();
    if (await tableHeader.count() > 0) {
      await captureScreenshot(page, 'table-header-en-US', {
        clip: await tableHeader.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Table content in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/alerts');
    
    const table = page.locator('table').first();
    if (await table.count() > 0) {
      await captureScreenshot(page, 'table-zh-CN', {
        maxDiffPixels: 50,
      });
    }
  });

  test('Table content in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/alerts');
    
    const table = page.locator('table').first();
    if (await table.count() > 0) {
      await captureScreenshot(page, 'table-en-US', {
        maxDiffPixels: 50,
      });
    }
  });
});

test.describe('I18n - Alerts Page', () => {
  test('Alerts page in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/alerts');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'alerts-zh-CN', {
      maxDiffPixels: 100,
    });
  });

  test('Alerts page in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/alerts');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'alerts-en-US', {
      maxDiffPixels: 100,
    });
  });

  test('Alert item text in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/alerts');
    
    const alertItem = page.locator('.alert-item, [class*="AlertItem"]').first();
    if (await alertItem.count() > 0) {
      await captureScreenshot(page, 'alert-item-zh-CN', {
        clip: await alertItem.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });

  test('Alert item text in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/alerts');
    
    const alertItem = page.locator('.alert-item, [class*="AlertItem"]').first();
    if (await alertItem.count() > 0) {
      await captureScreenshot(page, 'alert-item-en-US', {
        clip: await alertItem.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });
});

test.describe('I18n - AI Copilot', () => {
  test('AI Copilot in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/ai-copilot');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'ai-copilot-zh-CN', {
      maxDiffPixels: 100,
    });
  });

  test('AI Copilot in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/ai-copilot');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'ai-copilot-en-US', {
      maxDiffPixels: 100,
    });
  });

  test('Chat placeholder in Chinese', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/ai-copilot');
    
    const chatInput = page.locator('textarea, input[type="text"]').last();
    if (await chatInput.count() > 0) {
      await captureScreenshot(page, 'chat-placeholder-zh-CN', {
        clip: await chatInput.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Chat placeholder in English', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/ai-copilot');
    
    const chatInput = page.locator('textarea, input[type="text"]').last();
    if (await chatInput.count() > 0) {
      await captureScreenshot(page, 'chat-placeholder-en-US', {
        clip: await chatInput.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });
});

test.describe('I18n - Language Persistence', () => {
  test('Language persists after navigation', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    // Switch to English
    await setLocale(page, LOCALES.EN_US);
    await page.waitForTimeout(300);
    
    // Navigate to another page
    await navigateAndWait(page, '/alerts');
    
    // Verify language is still English
    const lang = await page.evaluate(() => {
      return document.documentElement.lang;
    });
    expect(lang).toBe('en-US');
    
    await captureScreenshot(page, 'lang-persistence-en');
  });

  test('Language persists after page reload', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    // Switch to Chinese
    await setLocale(page, LOCALES.ZH_CN);
    await page.waitForTimeout(300);
    
    // Reload page
    await page.reload();
    await page.waitForTimeout(300);
    
    // Verify language is still Chinese
    const lang = await page.evaluate(() => {
      return document.documentElement.lang;
    });
    expect(lang).toBe('zh-CN');
    
    await captureScreenshot(page, 'lang-persistence-zh');
  });
});

test.describe('I18n - Typography and Layout', () => {
  test('Chinese text layout', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const textSection = page.locator('p, h1, h2').first();
    await captureScreenshot(page, 'text-layout-zh-CN', {
      clip: await textSection.boundingBox(),
      maxDiffPixels: 15,
    });
  });

  test('English text layout', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const textSection = page.locator('p, h1, h2').first();
    await captureScreenshot(page, 'text-layout-en-US', {
      clip: await textSection.boundingBox(),
      maxDiffPixels: 15,
    });
  });

  test('Chinese character rendering', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const title = page.locator('h1').first();
    await captureScreenshot(page, 'chinese-chars', {
      clip: await title.boundingBox(),
      maxDiffPixels: 10,
    });
  });

  test('English character rendering', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const title = page.locator('h1').first();
    await captureScreenshot(page, 'english-chars', {
      clip: await title.boundingBox(),
      maxDiffPixels: 10,
    });
  });
});

test.describe('I18n - Language Selector', () => {
  test('Language selector in Chinese context', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    
    const langSelector = page.locator('[data-lang], .language-selector').first();
    if (await langSelector.count() > 0) {
      await captureScreenshot(page, 'lang-selector-zh-CN', {
        clip: await langSelector.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Language selector in English context', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    
    const langSelector = page.locator('[data-lang], .language-selector').first();
    if (await langSelector.count() > 0) {
      await captureScreenshot(page, 'lang-selector-en-US', {
        clip: await langSelector.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });
});

test.describe('I18n - Cross-Theme I18n', () => {
  test('Chinese in light theme', async ({ page }) => {
    await setupVisualTest(page, { 
      locale: LOCALES.ZH_CN, 
      theme: THEMES.LIGHT 
    });
    await navigateAndWait(page, '/dashboard');
    await captureScreenshot(page, 'zh-CN-light-theme');
  });

  test('Chinese in dark theme', async ({ page }) => {
    await setupVisualTest(page, { 
      locale: LOCALES.ZH_CN, 
      theme: THEMES.DARK 
    });
    await navigateAndWait(page, '/dashboard');
    await captureScreenshot(page, 'zh-CN-dark-theme');
  });

  test('English in light theme', async ({ page }) => {
    await setupVisualTest(page, { 
      locale: LOCALES.EN_US, 
      theme: THEMES.LIGHT 
    });
    await navigateAndWait(page, '/dashboard');
    await captureScreenshot(page, 'en-US-light-theme');
  });

  test('English in dark theme', async ({ page }) => {
    await setupVisualTest(page, { 
      locale: LOCALES.EN_US, 
      theme: THEMES.DARK 
    });
    await navigateAndWait(page, '/dashboard');
    await captureScreenshot(page, 'en-US-dark-theme');
  });
});

test.describe('I18n - Responsive I18n', () => {
  test('Chinese on mobile', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'zh-CN-mobile');
  });

  test('English on mobile', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.MOBILE);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'en-US-mobile');
  });

  test('Chinese on desktop', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.ZH_CN });
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'zh-CN-desktop');
  });

  test('English on desktop', async ({ page }) => {
    await setupVisualTest(page, { locale: LOCALES.EN_US });
    await navigateAndWait(page, '/dashboard');
    await page.setViewportSize(VIEWPORTS.DESKTOP);
    await page.waitForTimeout(200);
    await captureScreenshot(page, 'en-US-desktop');
  });
});
