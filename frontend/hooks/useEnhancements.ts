'use client'

// 🔧 P1 Enhancement: UI/UX Improvements
// Frontend enhancements for better user experience without modifying core architecture

import { useState, useEffect, useCallback } from 'react';

// ========================================
// 🔧 P1 Enhancement: Loading States
// ========================================
export interface LoadingState {
  isLoading: boolean;
  error: Error | null;
  data: any;
}

export function useLoadingState(initialLoading = false): LoadingState & {
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
  setData: (data: any) => void;
  reset: () => void;
} {
  const [isLoading, setIsLoading] = useState(initialLoading);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<any>(null);

  const setLoading = useCallback((loading: boolean) => {
    setIsLoading(loading);
  }, []);

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setData(null);
  }, []);

  return {
    isLoading,
    error,
    data,
    setLoading,
    setError,
    setData,
    reset,
  };
}

// ========================================
// 🔧 P1 Enhancement: Debounce Hook
// ========================================
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// ========================================
// 🔧 P1 Enhancement: Local Storage Hook
// ========================================
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error loading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(valueToStore));
        }
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, storedValue]
  );

  return [storedValue, setValue];
}

// ========================================
// 🔧 P1 Enhancement: Toast Notification
// ========================================
export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback(
    (type: ToastMessage['type'], message: string, duration = 3000) => {
      const id = Date.now().toString();
      const toast: ToastMessage = { id, type, message, duration };
      
      setToasts((prev) => [...prev, toast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    []
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const success = useCallback((message: string, duration?: number) => {
    addToast('success', message, duration);
  }, [addToast]);

  const error = useCallback((message: string, duration?: number) => {
    addToast('error', message, duration);
  }, [addToast]);

  const warning = useCallback((message: string, duration?: number) => {
    addToast('warning', message, duration);
  }, [addToast]);

  const info = useCallback((message: string, duration?: number) => {
    addToast('info', message, duration);
  }, [addToast]);

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };
}

// ========================================
// 🔧 P1 Enhancement: Modal Dialog Hook
// ========================================
export function useModal(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}

// ========================================
// 🔧 P1 Enhancement: Form Validation Hook
// ========================================
export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: string) => boolean | string;
}

export interface ValidationErrors {
  [key: string]: string;
}

export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  validationRules: Record<keyof T, ValidationRule>
) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<keyof T, boolean>>({} as any);

  const validate = useCallback((): boolean => {
    const newErrors: ValidationErrors = {};
    let isValid = true;

    Object.entries(validationRules).forEach(([field, rules]) => {
      const value = values[field as keyof T];
      const fieldErrors: string[] = [];

      if (rules.required && !value) {
        fieldErrors.push('This field is required');
      }

      if (rules.minLength && value && String(value).length < rules.minLength) {
        fieldErrors.push(`Minimum length is ${rules.minLength}`);
      }

      if (rules.maxLength && value && String(value).length > rules.maxLength) {
        fieldErrors.push(`Maximum length is ${rules.maxLength}`);
      }

      if (rules.pattern && value && !rules.pattern.test(String(value))) {
        fieldErrors.push('Invalid format');
      }

      if (rules.custom && value) {
        const customResult = rules.custom(String(value));
        if (customResult !== true) {
          fieldErrors.push(typeof customResult === 'string' ? customResult : 'Validation failed');
        }
      }

      if (fieldErrors.length > 0) {
        newErrors[field] = fieldErrors[0];
        isValid = false;
      }
    });

    setErrors(newErrors);
    return isValid;
  }, [values, validationRules]);

  const handleChange = useCallback(
    (field: keyof T, value: any) => {
      setValues((prev) => ({ ...prev, [field]: value }));
      setTouched((prev) => ({ ...prev, [field]: true }));
    },
    []
  );

  const handleBlur = useCallback((field: keyof T) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({} as any);
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validate,
    reset,
    isValid: Object.keys(errors).length === 0,
  };
}

// ========================================
// 🔧 P1 Enhancement: Responsive Breakpoints
// ========================================
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
};

export function useBreakpoint() {
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    ...windowSize,
    isMobile: windowSize.width < breakpoints.md,
    isTablet: windowSize.width >= breakpoints.md && windowSize.width < breakpoints.lg,
    isDesktop: windowSize.width >= breakpoints.lg,
  };
}

// ========================================
// 🔧 P1 Enhancement: Theme Management
// ========================================
export type Theme = 'light' | 'dark' | 'system';

export function useTheme() {
  const [theme, setTheme] = useLocalStorage<Theme>('theme', 'system');

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return { theme, setTheme };
}

// ========================================
// 🔧 P1 Enhancement: Keyboard Shortcuts
// ========================================
export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  options: { ctrl?: boolean; shift?: boolean; alt?: boolean } = {}
) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { ctrl = false, shift = false, alt = false } = options;

      if (
        event.key.toLowerCase() === key.toLowerCase() &&
        event.ctrlKey === ctrl &&
        event.shiftKey === shift &&
        event.altKey === alt
      ) {
        event.preventDefault();
        callback();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [key, callback, options]);
}

// ========================================
// 🔧 P1 Enhancement: Infinite Scroll Hook
// ========================================
export function useInfiniteScroll(
  callback: () => void,
  options: { threshold?: number; rootMargin?: string } = {}
) {
  const { threshold = 100, rootMargin = '0px' } = options;
  const [isFetching, setIsFetching] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (typeof window === 'undefined') return;

      const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      const isNearBottom = scrollTop + clientHeight >= scrollHeight - threshold;

      if (isNearBottom && !isFetching) {
        setIsFetching(true);
        callback();
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [callback, threshold, isFetching]);

  return { isFetching, setIsFetching };
}