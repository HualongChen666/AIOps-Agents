import { test, expect } from '@playwright/test';
import { 
  setupVisualTest, 
  navigateAndWait, 
  captureScreenshot, 
  hideDynamicElements,
  THEMES,
  LOCALES,
  VIEWPORTS
} from './visual-helpers';

/**
 * UI Consistency Visual Regression Tests
 * 
 * These tests ensure visual consistency across:
 * - Component styling
 * - Layout consistency
 * - Color schemes
 * - Typography
 * - Spacing and alignment
 */

test.describe('UI Consistency - Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page, {
      theme: THEMES.DARK,
      locale: LOCALES.ZH_CN,
    });
  });

  test('Dashboard page layout consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'dashboard-layout', {
      maxDiffPixels: 100,
      threshold: 0.3,
    });
  });

  test('Dashboard cards visual consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    await hideDynamicElements(page);
    
    // Capture just the cards section
    const cardsSection = page.locator('.grid').first();
    await captureScreenshot(page, 'dashboard-cards', {
      clip: await cardsSection.boundingBox(),
      maxDiffPixels: 50,
    });
  });

  test('Dashboard header consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const header = page.locator('h1').first();
    await captureScreenshot(page, 'dashboard-header', {
      clip: await header.boundingBox(),
      maxDiffPixels: 20,
    });
  });
});

test.describe('UI Consistency - Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Top navigation bar consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const topBar = page.locator('header').first();
    await captureScreenshot(page, 'top-navigation', {
      clip: await topBar.boundingBox(),
      maxDiffPixels: 30,
    });
  });

  test('Side navigation consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const sideNav = page.locator('aside').first();
    await captureScreenshot(page, 'side-navigation', {
      clip: await sideNav.boundingBox(),
      maxDiffPixels: 50,
    });
  });

  test('Navigation menu items consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const navItems = page.locator('nav a').first();
    await captureScreenshot(page, 'nav-menu-item', {
      clip: await navItems.boundingBox(),
      maxDiffPixels: 10,
    });
  });
});

test.describe('UI Consistency - Cards', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Card component consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const card = page.locator('.card, [class*="Card"]').first();
    if (await card.count() > 0) {
      await captureScreenshot(page, 'card-component', {
        clip: await card.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });

  test('Card header consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const cardHeader = page.locator('.card-header, [class*="CardHeader"]').first();
    if (await cardHeader.count() > 0) {
      await captureScreenshot(page, 'card-header', {
        clip: await cardHeader.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Card content consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const cardContent = page.locator('.card-content, [class*="CardContent"]').first();
    if (await cardContent.count() > 0) {
      await captureScreenshot(page, 'card-content', {
        clip: await cardContent.boundingBox(),
        maxDiffPixels: 50,
      });
    }
  });
});

test.describe('UI Consistency - Buttons', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Primary button consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const primaryButton = page.locator('button').first();
    if (await primaryButton.count() > 0) {
      await captureScreenshot(page, 'button-primary', {
        clip: await primaryButton.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Secondary button consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const buttons = page.locator('button');
    if (await buttons.count() > 1) {
      const secondaryButton = buttons.nth(1);
      await captureScreenshot(page, 'button-secondary', {
        clip: await secondaryButton.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});

test.describe('UI Consistency - Forms', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Input field consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const input = page.locator('input[type="text"]').first();
    if (await input.count() > 0) {
      await captureScreenshot(page, 'input-field', {
        clip: await input.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Select dropdown consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const select = page.locator('select').first();
    if (await select.count() > 0) {
      await captureScreenshot(page, 'select-dropdown', {
        clip: await select.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Form label consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const label = page.locator('label').first();
    if (await label.count() > 0) {
      await captureScreenshot(page, 'form-label', {
        clip: await label.boundingBox(),
        maxDiffPixels: 5,
      });
    }
  });
});

test.describe('UI Consistency - Tables', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Table header consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const tableHeader = page.locator('th').first();
    if (await tableHeader.count() > 0) {
      await captureScreenshot(page, 'table-header', {
        clip: await tableHeader.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });

  test('Table row consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const tableRow = page.locator('tr').nth(1); // Skip header row
    if (await tableRow.count() > 0) {
      await captureScreenshot(page, 'table-row', {
        clip: await tableRow.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Table cell consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const tableCell = page.locator('td').first();
    if (await tableCell.count() > 0) {
      await captureScreenshot(page, 'table-cell', {
        clip: await tableCell.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });
});

test.describe('UI Consistency - Status Indicators', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Status badge consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const badge = page.locator('.badge, [class*="Badge"]').first();
    if (await badge.count() > 0) {
      await captureScreenshot(page, 'status-badge', {
        clip: await badge.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Progress bar consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const progress = page.locator('.progress, [class*="Progress"]').first();
    if (await progress.count() > 0) {
      await captureScreenshot(page, 'progress-bar', {
        clip: await progress.boundingBox(),
        maxDiffPixels: 15,
      });
    }
  });
});

test.describe('UI Consistency - Alerts Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Alerts page layout', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'alerts-page-layout', {
      maxDiffPixels: 100,
    });
  });

  test('Alert item consistency', async ({ page }) => {
    await navigateAndWait(page, '/alerts');
    
    const alertItem = page.locator('.alert-item, [class*="AlertItem"]').first();
    if (await alertItem.count() > 0) {
      await captureScreenshot(page, 'alert-item', {
        clip: await alertItem.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });
});

test.describe('UI Consistency - AI Copilot', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('AI Copilot page layout', async ({ page }) => {
    await navigateAndWait(page, '/ai-copilot');
    await hideDynamicElements(page);
    await captureScreenshot(page, 'ai-copilot-layout', {
      maxDiffPixels: 100,
    });
  });

  test('Chat input consistency', async ({ page }) => {
    await navigateAndWait(page, '/ai-copilot');
    
    const chatInput = page.locator('textarea, input[type="text"]').last();
    if (await chatInput.count() > 0) {
      await captureScreenshot(page, 'chat-input', {
        clip: await chatInput.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });
});

test.describe('UI Consistency - Typography', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Heading typography consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const h1 = page.locator('h1').first();
    await captureScreenshot(page, 'typography-h1', {
      clip: await h1.boundingBox(),
      maxDiffPixels: 10,
    });
  });

  test('Subheading typography consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const h2 = page.locator('h2').first();
    if (await h2.count() > 0) {
      await captureScreenshot(page, 'typography-h2', {
        clip: await h2.boundingBox(),
        maxDiffPixels: 10,
      });
    }
  });

  test('Body text typography consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const paragraph = page.locator('p').first();
    await captureScreenshot(page, 'typography-body', {
      clip: await paragraph.boundingBox(),
      maxDiffPixels: 10,
    });
  });
});

test.describe('UI Consistency - Spacing', () => {
  test.beforeEach(async ({ page }) => {
    await setupVisualTest(page);
  });

  test('Card spacing consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const card = page.locator('.card, [class*="Card"]').first();
    if (await card.count() > 0) {
      await captureScreenshot(page, 'card-spacing', {
        clip: await card.boundingBox(),
        maxDiffPixels: 20,
      });
    }
  });

  test('Section spacing consistency', async ({ page }) => {
    await navigateAndWait(page, '/dashboard');
    
    const section = page.locator('.space-y-6, section').first();
    if (await section.count() > 0) {
      await captureScreenshot(page, 'section-spacing', {
        clip: await section.boundingBox(),
        maxDiffPixels: 30,
      });
    }
  });
});
