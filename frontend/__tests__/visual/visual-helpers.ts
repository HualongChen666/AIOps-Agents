import { Page, expect } from '@playwright/test';

/**
 * Visual Regression Test Helpers
 * 
 * Common utilities for visual regression testing including:
 * - Theme management
 * - Locale management
 * - Screenshot capture with consistent naming
 * - Responsive viewport handling
 */

export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
} as const;

export const LOCALES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US',
} as const;

export const VIEWPORTS = {
  MOBILE: { width: 375, height: 667 },
  MOBILE_LARGE: { width: 414, height: 896 },
  TABLET: { width: 768, height: 1024 },
  DESKTOP_SMALL: { width: 1024, height: 768 },
  DESKTOP: { width: 1280, height: 720 },
  DESKTOP_LARGE: { width: 1920, height: 1080 },
} as const;

/**
 * Set theme using localStorage and DOM manipulation
 */
export async function setTheme(page: Page, theme: 'light' | 'dark'): Promise<void> {
  await page.evaluate((t) => {
    localStorage.setItem('aiops-theme', t);
    const root = document.documentElement;
    if (t === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, theme);
  
  // Wait for theme to apply
  await page.waitForTimeout(100);
}

/**
 * Set locale using localStorage and cookies
 */
export async function setLocale(page: Page, locale: 'zh-CN' | 'en-US'): Promise<void> {
  await page.evaluate((l) => {
    localStorage.setItem('locale', l);
    document.documentElement.lang = l;
  }, locale);
  
  // Set cookie as well
  const cookies = [{
    name: 'locale',
    value: locale,
    domain: 'localhost',
    path: '/',
  }];
  await page.context().addCookies(cookies);
  
  // Wait for locale to apply
  await page.waitForTimeout(100);
}

/**
 * Capture screenshot with consistent naming and options
 */
export async function captureScreenshot(
  page: Page,
  name: string,
  options: {
    fullPage?: boolean;
    clip?: { x: number; y: number; width: number; height: number };
    maxDiffPixels?: number;
    threshold?: number;
  } = {}
): Promise<void> {
  const { fullPage = true, clip, maxDiffPixels = 0, threshold = 0.2 } = options;
  
  await expect(page).toHaveScreenshot(name, {
    fullPage,
    clip,
    maxDiffPixels,
    threshold,
    animations: 'disabled',
  });
}

/**
 * Wait for page to be stable (no network activity, animations complete)
 */
export async function waitForPageStable(page: Page): Promise<void> {
  // Wait for network to be idle
  await page.waitForLoadState('networkidle');
  
  // Wait for any animations to complete
  await page.waitForTimeout(300);
  
  // Wait for images to load
  await page.evaluate(() => {
    return new Promise((resolve) => {
      if (document.readyState === 'complete') {
        resolve(null);
      } else {
        window.addEventListener('load', () => resolve(null));
      }
    });
  });
}

/**
 * Navigate to page and wait for stability
 */
export async function navigateAndWait(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await waitForPageStable(page);
}

/**
 * Set viewport and capture screenshot
 */
export async function testViewport(
  page: Page,
  viewport: { width: number; height: number },
  screenshotName: string
): Promise<void> {
  await page.setViewportSize(viewport);
  await page.waitForTimeout(200); // Wait for responsive layout to adjust
  await captureScreenshot(page, screenshotName);
}

/**
 * Test component across multiple viewports
 */
export async function testResponsiveViewports(
  page: Page,
  basePath: string,
  component: string
): Promise<void> {
  const viewports = [
    VIEWPORTS.MOBILE,
    VIEWPORTS.MOBILE_LARGE,
    VIEWPORTS.TABLET,
    VIEWPORTS.DESKTOP_SMALL,
    VIEWPORTS.DESKTOP,
    VIEWPORTS.DESKTOP_LARGE,
  ];
  
  for (const viewport of viewports) {
    const sizeName = `${viewport.width}x${viewport.height}`;
    await testViewport(page, viewport, `${component}-${sizeName}`);
  }
}

/**
 * Test page with different themes
 */
export async function testThemes(
  page: Page,
  path: string,
  testName: string
): Promise<void> {
  // Test light theme
  await navigateAndWait(page, path);
  await setTheme(page, THEMES.LIGHT);
  await captureScreenshot(page, `${testName}-light`);
  
  // Test dark theme
  await setTheme(page, THEMES.DARK);
  await captureScreenshot(page, `${testName}-dark`);
}

/**
 * Test page with different locales
 */
export async function testLocales(
  page: Page,
  path: string,
  testName: string
): Promise<void> {
  // Test Chinese
  await navigateAndWait(page, path);
  await setLocale(page, LOCALES.ZH_CN);
  await captureScreenshot(page, `${testName}-zh-CN`);
  
  // Test English
  await setLocale(page, LOCALES.EN_US);
  await captureScreenshot(page, `${testName}-en-US`);
}

/**
 * Comprehensive visual test: themes, locales, and viewports
 */
export async function comprehensiveVisualTest(
  page: Page,
  path: string,
  testName: string
): Promise<void> {
  // Test with both themes
  for (const theme of [THEMES.LIGHT, THEMES.DARK]) {
    await navigateAndWait(page, path);
    await setTheme(page, theme);
    
    // Test with both locales
    for (const locale of [LOCALES.ZH_CN, LOCALES.EN_US]) {
      await setLocale(page, locale);
      
      // Test across key viewports
      await testViewport(page, VIEWPORTS.DESKTOP, `${testName}-${theme}-${locale}-desktop`);
      await testViewport(page, VIEWPORTS.TABLET, `${testName}-${theme}-${locale}-tablet`);
      await testViewport(page, VIEWPORTS.MOBILE, `${testName}-${theme}-${locale}-mobile`);
    }
  }
}

/**
 * Hide dynamic elements that shouldn't affect visual regression
 */
export async function hideDynamicElements(page: Page): Promise<void> {
  await page.evaluate(() => {
    // Hide timestamps
    const timestamps = document.querySelectorAll('[data-timestamp], .timestamp, time');
    timestamps.forEach(el => (el as HTMLElement).style.visibility = 'hidden');
    
    // Hide loading spinners
    const loaders = document.querySelectorAll('.loading, .spinner, [data-loading]');
    loaders.forEach(el => (el as HTMLElement).style.display = 'none');
    
    // Hide animated elements
    const animated = document.querySelectorAll('[data-animate], .animate');
    animated.forEach(el => (el as HTMLElement).style.animation = 'none');
  });
}

/**
 * Mock authentication for visual tests
 */
export async function mockAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.setItem('auth_token', 'mock-token-for-visual-tests');
    localStorage.setItem('user_id', 'test-user');
  });
}

/**
 * Setup page for visual testing
 */
export async function setupVisualTest(
  page: Page,
  options: {
    theme?: 'light' | 'dark';
    locale?: 'zh-CN' | 'en-US';
    mockAuth?: boolean;
  } = {}
): Promise<void> {
  const { theme = THEMES.DARK, locale = LOCALES.ZH_CN, mockAuth: shouldMockAuth = true } = options;
  
  if (shouldMockAuth) {
    await mockAuth(page);
  }
  
  await setTheme(page, theme);
  await setLocale(page, locale);
}
