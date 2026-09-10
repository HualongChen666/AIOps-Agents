import {
  generateAriaLabel,
  generateAriaDescription,
  checkContrastRatio,
  keyboardNavigation,
  screenReader,
  focusManagement,
  formAccessibility,
  tableAccessibility,
  modalAccessibility,
  skipLink,
} from '@/lib/accessibility';

describe('lib/accessibility', () => {
  describe('generateAriaLabel', () => {
    it('returns only the action when no target/description is given', () => {
      expect(generateAriaLabel('Delete')).toBe('Delete');
    });

    it('appends the target when provided', () => {
      expect(generateAriaLabel('Delete', 'user')).toBe('Delete user');
    });

    it('appends both target and description', () => {
      expect(generateAriaLabel('Delete', 'user', 'permanently')).toBe(
        'Delete user permanently'
      );
    });

    it('skips empty target but keeps description', () => {
      expect(generateAriaLabel('Open', '', 'settings')).toBe('Open settings');
    });
  });

  describe('generateAriaDescription', () => {
    it('returns the component name alone', () => {
      expect(generateAriaDescription('Chart')).toBe('Chart');
    });

    it('joins component and state with a period', () => {
      expect(generateAriaDescription('Chart', 'loading')).toBe('Chart. loading');
    });

    it('joins component, state and additional info', () => {
      expect(generateAriaDescription('Chart', 'loading', 'please wait')).toBe(
        'Chart. loading. please wait'
      );
    });

    it('skips empty state but keeps additional info', () => {
      expect(generateAriaDescription('Chart', '', 'details')).toBe('Chart. details');
    });
  });

  describe('checkContrastRatio', () => {
    it('computes the maximum ratio for black on white (21:1)', () => {
      const { ratio, passesAA, passesAAA } = checkContrastRatio('#000000', '#ffffff');
      expect(ratio).toBeCloseTo(21, 1);
      expect(passesAA).toBe(true);
      expect(passesAAA).toBe(true);
    });

    it('reports ratio 1 and failure for identical colors', () => {
      const { ratio, passesAA, passesAAA } = checkContrastRatio('#ffffff', '#ffffff');
      expect(ratio).toBeCloseTo(1, 5);
      expect(passesAA).toBe(false);
      expect(passesAAA).toBe(false);
    });

    it('accepts colors without the leading hash', () => {
      const { ratio } = checkContrastRatio('000000', 'ffffff');
      expect(ratio).toBeCloseTo(21, 1);
    });

    it('falls back to black for a malformed hex string', () => {
      const { ratio } = checkContrastRatio('not-a-color', '#ffffff');
      expect(ratio).toBeCloseTo(21, 1);
    });
  });

  describe('keyboardNavigation.handleKeyDown', () => {
    const makeEvent = (key: string) =>
      ({ key, preventDefault: jest.fn() } as unknown as React.KeyboardEvent);

    it('invokes the Enter handler without preventing default', () => {
      const onEnter = jest.fn();
      const e = makeEvent('Enter');
      keyboardNavigation.handleKeyDown(e, { onEnter });
      expect(onEnter).toHaveBeenCalledTimes(1);
      expect(e.preventDefault).not.toHaveBeenCalled();
    });

    it('invokes the Escape handler', () => {
      const onEscape = jest.fn();
      keyboardNavigation.handleKeyDown(makeEvent('Escape'), { onEscape });
      expect(onEscape).toHaveBeenCalledTimes(1);
    });

    it('invokes arrow handlers and prevents default scrolling', () => {
      const handlers = {
        onArrowUp: jest.fn(),
        onArrowDown: jest.fn(),
        onArrowLeft: jest.fn(),
        onArrowRight: jest.fn(),
      };
      for (const key of ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'] as const) {
        const e = makeEvent(key);
        keyboardNavigation.handleKeyDown(e, handlers);
        expect(e.preventDefault).toHaveBeenCalledTimes(1);
      }
      expect(handlers.onArrowUp).toHaveBeenCalled();
      expect(handlers.onArrowDown).toHaveBeenCalled();
      expect(handlers.onArrowLeft).toHaveBeenCalled();
      expect(handlers.onArrowRight).toHaveBeenCalled();
    });

    it('handles the space key and prevents default page scroll', () => {
      const onSpace = jest.fn();
      const e = makeEvent(' ');
      keyboardNavigation.handleKeyDown(e, { onSpace });
      expect(onSpace).toHaveBeenCalledTimes(1);
      expect(e.preventDefault).toHaveBeenCalledTimes(1);
    });

    it('handles the Tab key without preventing default (focus moves natively)', () => {
      const onTab = jest.fn();
      const e = makeEvent('Tab');
      keyboardNavigation.handleKeyDown(e, { onTab });
      expect(onTab).toHaveBeenCalledTimes(1);
      expect(e.preventDefault).not.toHaveBeenCalled();
    });

    it('does nothing for unhandled keys', () => {
      const e = makeEvent('a');
      keyboardNavigation.handleKeyDown(e, { onEnter: jest.fn() });
      expect(e.preventDefault).not.toHaveBeenCalled();
    });
  });

  describe('keyboardNavigation.getShortcutHint', () => {
    afterEach(() => {
      Object.defineProperty(navigator, 'platform', { value: '', configurable: true });
    });

    it('uses Ctrl on non-mac platforms', () => {
      Object.defineProperty(navigator, 'platform', { value: 'Win32', configurable: true });
      expect(keyboardNavigation.getShortcutHint(['K'])).toBe('Ctrl+K');
    });

    it('uses the command glyph on mac platforms', () => {
      Object.defineProperty(navigator, 'platform', { value: 'MacIntel', configurable: true });
      expect(keyboardNavigation.getShortcutHint(['K'])).toBe('⌘+K');
    });

    it('joins multiple shortcuts with a comma', () => {
      Object.defineProperty(navigator, 'platform', { value: 'Win32', configurable: true });
      expect(keyboardNavigation.getShortcutHint(['K', 'S'])).toBe('Ctrl+K, Ctrl+S');
    });
  });

  describe('screenReader', () => {
    it('announces a message in a polite live region and removes it after 1s', () => {
      jest.useFakeTimers();
      screenReader.announce('Saved');
      const region = document.querySelector('[role="status"].sr-only');
      expect(region).not.toBeNull();
      expect(region).toHaveAttribute('aria-live', 'polite');
      expect(region).toHaveAttribute('aria-atomic', 'true');
      expect(region).toHaveTextContent('Saved');
      jest.advanceTimersByTime(1000);
      expect(document.querySelector('[role="status"].sr-only')).toBeNull();
      jest.useRealTimers();
    });

    it('gets polite live region props by default', () => {
      expect(screenReader.getLiveRegionProps()).toEqual({
        role: 'status',
        'aria-live': 'polite',
        'aria-atomic': 'true',
      });
    });

    it('gets assertive live region props when polite is false', () => {
      expect(screenReader.getLiveRegionProps(false)).toMatchObject({
        role: 'status',
        'aria-live': 'assertive',
      });
    });
  });

  describe('focusManagement', () => {
    it('traps focus and wraps Tab/Shift+Tab within the container', () => {
      const container = document.createElement('div');
      const first = document.createElement('button');
      const last = document.createElement('button');
      first.textContent = 'first';
      last.textContent = 'last';
      container.append(first, last);
      document.body.appendChild(container);

      const cleanup = focusManagement.trapFocus(container);
      expect(first).toHaveFocus();

      last.focus();
      container.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
      expect(first).toHaveFocus();

      first.focus();
      container.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true }));
      expect(last).toHaveFocus();

      cleanup();
      document.body.removeChild(container);
    });

    it('restores focus to a previously active element', () => {
      const el = document.createElement('button');
      document.body.appendChild(el);
      focusManagement.restoreFocus(el);
      expect(el).toHaveFocus();
      document.body.removeChild(el);
    });

    it('restoreFocus is a no-op when there is no previous element', () => {
      expect(() => focusManagement.restoreFocus(null)).not.toThrow();
    });
  });

  describe('formAccessibility', () => {
    it('builds field props with no error', () => {
      expect(formAccessibility.getFieldProps('Email')).toEqual({
        'aria-label': 'Email',
        'aria-invalid': false,
        'aria-describedby': undefined,
        'aria-required': false,
      });
    });

    it('wires the error id when an error is present', () => {
      expect(formAccessibility.getFieldProps('Email', 'invalid', true)).toEqual({
        'aria-label': 'Email',
        'aria-invalid': true,
        'aria-describedby': 'Email-error',
        'aria-required': true,
      });
    });

    it('builds error message props', () => {
      expect(formAccessibility.getErrorProps('Email')).toEqual({
        id: 'Email-error',
        role: 'alert',
        'aria-live': 'polite',
      });
    });
  });

  describe('tableAccessibility', () => {
    it('builds table props', () => {
      expect(tableAccessibility.getTableProps('Users')).toEqual({
        role: 'table',
        'aria-label': 'Users',
      });
    });

    it('builds header cell props with a scope', () => {
      expect(tableAccessibility.getCellProps(true, 'col')).toEqual({
        role: 'columnheader',
        scope: 'col',
      });
    });

    it('builds body cell props without a scope', () => {
      expect(tableAccessibility.getCellProps(false)).toEqual({
        role: 'cell',
        scope: undefined,
      });
    });
  });

  describe('modalAccessibility', () => {
    it('builds modal props reflecting open state', () => {
      expect(modalAccessibility.getModalProps('Settings', true)).toEqual({
        role: 'dialog',
        'aria-modal': 'true',
        'aria-labelledby': 'Settings-title',
        'aria-hidden': false,
      });
    });

    it('marks a closed modal as hidden', () => {
      expect(modalAccessibility.getModalProps('Settings', false)['aria-hidden']).toBe(true);
    });

    it('builds backdrop props', () => {
      expect(modalAccessibility.getBackdropProps()).toEqual({ 'aria-hidden': 'true' });
    });
  });

  describe('skipLink', () => {
    it('builds a skip link to the given target with a default label', () => {
      const props = skipLink.getSkipLinkProps('main');
      expect(props.href).toBe('#main');
      expect(props['aria-label']).toBe('Skip to main content');
      expect(props.className).toContain('sr-only');
    });

    it('accepts a custom label', () => {
      expect(skipLink.getSkipLinkProps('main', '跳到主内容')['aria-label']).toBe('跳到主内容');
    });
  });
});
