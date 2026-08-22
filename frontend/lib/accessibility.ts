/**
 * Accessibility Utilities
 *
 * Provides accessibility utilities for ARIA labels, keyboard navigation,
 * screen reader support, and contrast optimization.
 */

/**
 * Generate ARIA label for interactive elements
 */
export function generateAriaLabel(
  action: string,
  target?: string,
  description?: string
): string {
  const parts = [action];
  if (target) parts.push(target);
  if (description) parts.push(description);
  return parts.join(' ');
}

/**
 * Generate ARIA description for complex components
 */
export function generateAriaDescription(
  component: string,
  state?: string,
  additionalInfo?: string
): string {
  const parts = [component];
  if (state) parts.push(state);
  if (additionalInfo) parts.push(additionalInfo);
  return parts.join('. ');
}

/**
 * Check color contrast ratio (WCAG AA requires 4.5:1 for normal text)
 */
export function checkContrastRatio(
  foreground: string,
  background: string
): { ratio: number; passesAA: boolean; passesAAA: boolean } {
  // Simple implementation - in production use a proper color contrast library
  const hexToRgb = (hex: string) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
      : { r: 0, g: 0, b: 0 };
  };

  const fg = hexToRgb(foreground);
  const bg = hexToRgb(background);

  const luminance = (r: number, g: number, b: number) => {
    const a = [r, g, b].map((v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
  };

  const lum1 = luminance(fg.r, fg.g, fg.b);
  const lum2 = luminance(bg.r, bg.g, bg.b);
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);

  const ratio = (brightest + 0.05) / (darkest + 0.05);

  return {
    ratio,
    passesAA: ratio >= 4.5,
    passesAAA: ratio >= 7,
  };
}

/**
 * Keyboard navigation utilities
 */
export const keyboardNavigation = {
  /**
   * Handle keyboard events for custom components
   */
  handleKeyDown: (
    event: React.KeyboardEvent,
    handlers: {
      onEnter?: () => void;
      onEscape?: () => void;
      onArrowUp?: () => void;
      onArrowDown?: () => void;
      onArrowLeft?: () => void;
      onArrowRight?: () => void;
      onSpace?: () => void;
      onTab?: () => void;
    }
  ) => {
    switch (event.key) {
      case 'Enter':
        handlers.onEnter?.();
        break;
      case 'Escape':
        handlers.onEscape?.();
        break;
      case 'ArrowUp':
        handlers.onArrowUp?.();
        event.preventDefault();
        break;
      case 'ArrowDown':
        handlers.onArrowDown?.();
        event.preventDefault();
        break;
      case 'ArrowLeft':
        handlers.onArrowLeft?.();
        event.preventDefault();
        break;
      case 'ArrowRight':
        handlers.onArrowRight?.();
        event.preventDefault();
        break;
      case ' ':
        handlers.onSpace?.();
        event.preventDefault();
        break;
      case 'Tab':
        handlers.onTab?.();
        break;
    }
  },

  /**
   * Generate keyboard shortcut hint
   */
  getShortcutHint: (keys: string[]) => {
    const platform = navigator.platform.toLowerCase();
    const modifier = platform.includes('mac') ? '⌘' : 'Ctrl';
    return keys.map(key => `${modifier}+${key}`).join(', ');
  },
};

/**
 * Screen reader utilities
 */
export const screenReader = {
  /**
   * Announce changes to screen readers
   */
  announce: (message: string) => {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    document.body.appendChild(announcement);
    setTimeout(() => document.body.removeChild(announcement), 1000);
  },

  /**
   * Generate ARIA live region attributes
   */
  getLiveRegionProps: (polite = true) => ({
    role: 'status' as const,
    'aria-live': polite ? 'polite' : 'assertive',
    'aria-atomic': 'true',
  }),
};

/**
 * Focus management utilities
 */
export const focusManagement = {
  /**
   * Trap focus within a container
   */
  trapFocus: (container: HTMLElement) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    firstElement?.focus();

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  },

  /**
   * Restore focus after modal close
   */
  restoreFocus: (previousActiveElement: HTMLElement | null) => {
    if (previousActiveElement) {
      previousActiveElement.focus();
    }
  },
};

/**
 * Form accessibility utilities
 */
export const formAccessibility = {
  /**
   * Generate ARIA attributes for form fields
   */
  getFieldProps: (label: string, error?: string, required = false) => ({
    'aria-label': label,
    'aria-invalid': !!error,
    'aria-describedby': error ? `${label}-error` : undefined,
    'aria-required': required,
  }),

  /**
   * Generate error message props
   */
  getErrorProps: (fieldId: string) => ({
    id: `${fieldId}-error`,
    role: 'alert' as const,
    'aria-live': 'polite' as const,
  }),
};

/**
 * Table accessibility utilities
 */
export const tableAccessibility = {
  /**
   * Generate ARIA attributes for tables
   */
  getTableProps: (caption: string) => ({
    role: 'table' as const,
    'aria-label': caption,
  }),

  /**
   * Generate cell props for accessibility
   */
  getCellProps: (isHeader = false, scope?: 'col' | 'row') => ({
    role: isHeader ? 'columnheader' : 'cell' as const,
    scope: isHeader ? scope : undefined,
  }),
};

/**
 * Modal accessibility utilities
 */
export const modalAccessibility = {
  /**
   * Generate ARIA attributes for modals
   */
  getModalProps: (title: string, isOpen: boolean) => ({
    role: 'dialog' as const,
    'aria-modal': 'true' as const,
    'aria-labelledby': `${title}-title`,
    'aria-hidden': !isOpen,
  }),

  /**
   * Generate backdrop props
   */
  getBackdropProps: () => ({
    'aria-hidden': 'true' as const,
  }),
};

/**
 * Skip link utilities
 */
export const skipLink = {
  /**
   * Generate skip link props
   */
  getSkipLinkProps: (targetId: string, label = 'Skip to main content') => ({
    href: `#${targetId}`,
    className: 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded',
    'aria-label': label,
  }),
};