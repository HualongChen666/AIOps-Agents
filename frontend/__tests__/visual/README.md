# Visual Regression Tests

This directory contains comprehensive visual regression tests for the AIOps Agent frontend using Playwright.

## Overview

Visual regression tests ensure UI consistency across:
- **UI Consistency**: Component styling, layout, typography, spacing
- **Responsive Design**: Mobile, tablet, desktop, and large screen viewports
- **Theme Switching**: Light and dark theme support
- **Internationalization**: Chinese (zh-CN) and English (en-US) support

## Test Structure

```
__tests__/visual/
├── visual-helpers.ts          # Common utilities and helpers
├── ui-consistency.visual.ts   # UI consistency tests
├── responsive.visual.ts       # Responsive design tests
├── theme-switching.visual.ts  # Theme switching tests
├── i18n.visual.ts            # Internationalization tests
└── README.md                 # This file
```

## Test Files

### 1. UI Consistency Tests (`ui-consistency.visual.ts`)
Tests for visual consistency across:
- Dashboard page layout
- Navigation components (top bar, side nav)
- Cards and headers
- Buttons and forms
- Tables and status indicators
- Typography and spacing
- Alerts page
- AI Copilot interface

**Test Count**: ~40 test cases

### 2. Responsive Design Tests (`responsive.visual.ts`)
Tests for responsive behavior across:
- Mobile viewports (375px, 414px)
- Tablet viewports (768px, 1024px)
- Desktop viewports (1024px, 1280px, 1920px)
- Navigation adaptation
- Grid layouts
- Form layouts
- Table responsiveness
- Chart rendering
- Breakpoint testing
- Orientation testing

**Test Count**: ~35 test cases

### 3. Theme Switching Tests (`theme-switching.visual.ts`)
Tests for theme functionality:
- Light theme rendering
- Dark theme rendering
- Theme toggle functionality
- Theme persistence
- Component-specific theme styling
- Color contrast and accessibility
- Navigation theme adaptation
- Card theme adaptation
- Form theme adaptation
- Table theme adaptation

**Test Count**: ~45 test cases

### 4. Internationalization Tests (`i18n.visual.ts`)
Tests for i18n functionality:
- Chinese (zh-CN) rendering
- English (en-US) rendering
- Language switching
- Navigation localization
- Card and header localization
- Button and form localization
- Table localization
- Language persistence
- Typography and layout
- Cross-theme i18n
- Responsive i18n

**Test Count**: ~50 test cases

## Running Tests

### Run all visual tests
```bash
npm run test:visual
```

### Run visual tests with UI mode
```bash
npm run test:visual:ui
```

### Run visual tests in headed mode (watch browser)
```bash
npm run test:visual:headed
```

### Update visual baselines
```bash
npm run test:visual:update
```

### View test report
```bash
npm run test:visual:report
```

## Configuration

The visual tests use a custom Playwright configuration (`playwright.config.ts`) with:

- **Multiple Projects**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari, Tablet
- **Viewport Sizes**: Mobile (375x667, 414x896), Tablet (768x1024, 1024x768), Desktop (1280x720, 1920x1080)
- **Screenshot Options**: Only on failure, with animations disabled
- **Retry Logic**: 2 retries on CI
- **Web Server**: Automatically starts dev server on http://localhost:3000

## Test Helpers

The `visual-helpers.ts` file provides utility functions:

- `setTheme(page, theme)`: Set light/dark theme
- `setLocale(page, locale)`: Set zh-CN/en-US locale
- `captureScreenshot(page, name, options)`: Capture screenshot with options
- `waitForPageStable(page)`: Wait for page to stabilize
- `navigateAndWait(page, path)`: Navigate and wait for stability
- `testViewport(page, viewport, name)`: Test specific viewport
- `testResponsiveViewports(page, path, component)`: Test across all viewports
- `testThemes(page, path, testName)`: Test both themes
- `testLocales(page, path, testName)`: Test both locales
- `hideDynamicElements(page)`: Hide timestamps, loaders, animations
- `mockAuth(page)`: Mock authentication for tests
- `setupVisualTest(page, options)`: Setup page for visual testing

## Visual Baselines

When running tests for the first time, Playwright will create baseline screenshots in:
```
test-results/visual/
└── [project-name]/
    └── [test-file]/
        └── [screenshot-name].png
```

## Test Results

After running tests, results are available in:
- **HTML Report**: `test-results/visual/index.html`
- **JSON Report**: `test-results/visual/visual-results.json`
- **Screenshots**: `test-results/visual/` (on failure)
- **Traces**: `test-results/visual/` (on retry)

## Coverage

### Pages Covered
- ✅ Dashboard (`/dashboard`)
- ✅ Alerts (`/alerts`)
- ✅ AI Copilot (`/ai-copilot`)

### Components Covered
- ✅ Navigation (Top Bar, Side Nav)
- ✅ Cards and Headers
- ✅ Buttons and Forms
- ✅ Tables
- ✅ Status Indicators
- ✅ Charts
- ✅ Chat Interface

### Themes Covered
- ✅ Light Theme
- ✅ Dark Theme

### Locales Covered
- ✅ Chinese (zh-CN)
- ✅ English (en-US)

### Viewports Covered
- ✅ Mobile (375x667, 414x896)
- ✅ Tablet (768x1024, 1024x768)
- ✅ Desktop (1024x768, 1280x720, 1920x1080)

## Best Practices

1. **Run tests before committing**: Ensure visual changes are intentional
2. **Update baselines carefully**: Only update when visual changes are expected
3. **Review failures**: Always review visual diff to understand changes
4. **Use UI mode for debugging**: `npm run test:visual:ui` for interactive debugging
5. **Hide dynamic elements**: Use `hideDynamicElements()` to avoid false positives
6. **Wait for stability**: Always use `waitForPageStable()` before capturing

## Troubleshooting

### Tests fail due to timing
- Increase wait time in `waitForPageStable()`
- Add specific waits for dynamic content

### Tests fail due to authentication
- Ensure `mockAuth()` is called in test setup
- Check that auth tokens are set correctly

### Visual differences are too strict
- Adjust `maxDiffPixels` in `captureScreenshot()`
- Adjust `threshold` for color tolerance

### Tests timeout
- Increase timeout in `playwright.config.ts`
- Check if dev server is starting correctly

## Integration with CI

Add to your CI pipeline:

```yaml
- name: Run Visual Regression Tests
  run: npm run test:visual
- name: Upload Visual Test Results
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: visual-test-results
    path: test-results/visual/
```

## Future Enhancements

- [ ] Add more page coverage (Overview, Settings, etc.)
- [ ] Add component-specific visual tests
- [ ] Add accessibility visual tests
- [ ] Add performance visual tests
- [ ] Add cross-browser visual comparison
- [ ] Add visual regression for charts and graphs
- [ ] Add visual regression for animations
- [ ] Add visual regression for error states

## Statistics

- **Total Test Files**: 4
- **Total Test Cases**: ~170
- **Total Screenshots**: ~500+
- **Languages Supported**: 2 (zh-CN, en-US)
- **Themes Supported**: 2 (light, dark)
- **Viewport Sizes**: 6
- **Browsers Supported**: 3 (Chromium, Firefox, WebKit)
