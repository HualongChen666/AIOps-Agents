import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useLoadingState,
  useDebounce,
  useLocalStorage,
  useToast,
  useModal,
  useFormValidation,
  useBreakpoint,
  useTheme,
  useKeyboardShortcut,
  useInfiniteScroll,
} from '@/hooks/useEnhancements';

describe('useLoadingState', () => {
  it('should initialize with default values', () => {
    const { result } = renderHook(() => useLoadingState());

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it('should initialize with custom loading state', () => {
    const { result } = renderHook(() => useLoadingState(true));

    expect(result.current.isLoading).toBe(true);
  });

  it('should update loading state', () => {
    const { result } = renderHook(() => useLoadingState());

    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('should update error state', () => {
    const { result } = renderHook(() => useLoadingState());
    const error = new Error('Test error');

    act(() => {
      result.current.setError(error);
    });

    expect(result.current.error).toBe(error);
  });

  it('should update data state', () => {
    const { result } = renderHook(() => useLoadingState());
    const data = { test: 'data' };

    act(() => {
      result.current.setData(data);
    });

    expect(result.current.data).toBe(data);
  });

  it('should reset all states', () => {
    const { result } = renderHook(() => useLoadingState());

    act(() => {
      result.current.setLoading(true);
      result.current.setError(new Error('Test'));
      result.current.setData({ test: 'data' });
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });
});

describe('useDebounce', () => {
  jest.useFakeTimers();

  it('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('test', 500));

    expect(result.current).toBe('test');
  });

  it('should debounce value changes', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    expect(result.current).toBe('initial');

    rerender({ value: 'updated', delay: 500 });

    expect(result.current).toBe('initial');

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe('updated');
  });

  it('should not update before delay', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 1000 } }
    );

    rerender({ value: 'updated', delay: 1000 });

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe('initial');
  });

  afterEach(() => {
    jest.useRealTimers();
  });
});

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should initialize with default value when key does not exist', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));

    expect(result.current[0]).toBe('default');
  });

  it('should load value from localStorage', () => {
    localStorage.setItem('test-key', JSON.stringify('stored-value'));

    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));

    expect(result.current[0]).toBe('stored-value');
  });

  it('should save value to localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));

    act(() => {
      result.current[1]('new-value');
    });

    expect(localStorage.getItem('test-key')).toBe(JSON.stringify('new-value'));
  });

  it('should handle function updates', () => {
    const { result } = renderHook(() => useLocalStorage('count', 0));

    act(() => {
      result.current[1]((prev: number) => prev + 1);
    });

    expect(result.current[0]).toBe(1);
  });

  it('should handle JSON parse errors', () => {
    localStorage.setItem('test-key', 'invalid-json');

    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));

    expect(result.current[0]).toBe('default');
  });
});

describe('useToast', () => {
  it('should initialize with empty toasts', () => {
    const { result } = renderHook(() => useToast());

    expect(result.current.toasts).toEqual([]);
  });

  it('should add success toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Success message');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('success');
    expect(result.current.toasts[0].message).toBe('Success message');
  });

  it('should add error toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.error('Error message');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('error');
  });

  it('should add warning toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.warning('Warning message');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('warning');
  });

  it('should add info toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.info('Info message');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('info');
  });

  it('should remove toast by id', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Test message');
    });

    const toastId = result.current.toasts[0].id;

    act(() => {
      result.current.removeToast(toastId);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('should auto-remove toast after duration', () => {
    jest.useFakeTimers();
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Test message', 1000);
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.toasts).toHaveLength(0);
    jest.useRealTimers();
  });
});

describe('useModal', () => {
  it('should initialize with closed state', () => {
    const { result } = renderHook(() => useModal());

    expect(result.current.isOpen).toBe(false);
  });

  it('should initialize with custom open state', () => {
    const { result } = renderHook(() => useModal(true));

    expect(result.current.isOpen).toBe(true);
  });

  it('should open modal', () => {
    const { result } = renderHook(() => useModal());

    act(() => {
      result.current.open();
    });

    expect(result.current.isOpen).toBe(true);
  });

  it('should close modal', () => {
    const { result } = renderHook(() => useModal(true));

    act(() => {
      result.current.close();
    });

    expect(result.current.isOpen).toBe(false);
  });

  it('should toggle modal', () => {
    const { result } = renderHook(() => useModal());

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isOpen).toBe(true);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isOpen).toBe(false);
  });
});

describe('useFormValidation', () => {
  it('should initialize with form values', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: '', email: '' },
        {
          username: { required: true },
          email: { required: true, pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ },
        }
      )
    );

    expect(result.current.values).toEqual({ username: '', email: '' });
  });

  it('should validate required fields', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: '', email: '' },
        {
          username: { required: true },
          email: { required: true },
        }
      )
    );

    act(() => {
      result.current.validate();
    });

    expect(result.current.errors.username).toBe('This field is required');
    expect(result.current.errors.email).toBe('This field is required');
  });

  it('should validate minLength', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: 'ab' },
        {
          username: { minLength: 3 },
        }
      )
    );

    act(() => {
      result.current.validate();
    });

    expect(result.current.errors.username).toBe('Minimum length is 3');
  });

  it('should validate maxLength', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: 'abcdefghijk' },
        {
          username: { maxLength: 10 },
        }
      )
    );

    act(() => {
      result.current.validate();
    });

    expect(result.current.errors.username).toBe('Maximum length is 10');
  });

  it('should validate pattern', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { email: 'invalid-email' },
        {
          email: { pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ },
        }
      )
    );

    act(() => {
      result.current.validate();
    });

    expect(result.current.errors.email).toBe('Invalid format');
  });

  it('should validate custom rules', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { password: '123' },
        {
          password: { custom: (value) => value.length >= 8 || 'Password too short' },
        }
      )
    );

    act(() => {
      result.current.validate();
    });

    expect(result.current.errors.password).toBe('Password too short');
  });

  it('should handle field changes', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: '' },
        {
          username: { required: true },
        }
      )
    );

    act(() => {
      result.current.handleChange('username', 'testuser');
    });

    expect(result.current.values.username).toBe('testuser');
  });

  it('should mark field as touched on change', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: '' },
        {
          username: { required: true },
        }
      )
    );

    act(() => {
      result.current.handleChange('username', 'test');
    });

    expect(result.current.touched.username).toBe(true);
  });

  it('should reset form', () => {
    const { result } = renderHook(() =>
      useFormValidation(
        { username: 'test' },
        {
          username: { required: true },
        }
      )
    );

    act(() => {
      result.current.handleChange('username', 'modified');
      result.current.reset();
    });

    expect(result.current.values).toEqual({ username: 'test' });
    expect(result.current.errors).toEqual({});
    expect(result.current.touched).toEqual({});
  });
});

describe('useBreakpoint', () => {
  it('should initialize with window size', () => {
    const { result } = renderHook(() => useBreakpoint());

    expect(result.current.width).toBe(window.innerWidth);
    expect(result.current.height).toBe(window.innerHeight);
  });

  it('should detect mobile breakpoint', () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 500,
    });

    const { result } = renderHook(() => useBreakpoint());

    expect(result.current.isMobile).toBe(true);
    expect(result.current.isTablet).toBe(false);
    expect(result.current.isDesktop).toBe(false);
  });

  it('should detect tablet breakpoint', () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 900,
    });

    const { result } = renderHook(() => useBreakpoint());

    expect(result.current.isMobile).toBe(false);
    expect(result.current.isTablet).toBe(true);
    expect(result.current.isDesktop).toBe(false);
  });

  it('should detect desktop breakpoint', () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200,
    });

    const { result } = renderHook(() => useBreakpoint());

    expect(result.current.isMobile).toBe(false);
    expect(result.current.isTablet).toBe(false);
    expect(result.current.isDesktop).toBe(true);
  });
});

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('light', 'dark');
  });

  it('should initialize with system theme', () => {
    const { result } = renderHook(() => useTheme());

    expect(result.current.theme).toBe('system');
  });

  it('should set light theme', () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme('light');
    });

    expect(result.current.theme).toBe('light');
    expect(document.documentElement.classList.contains('light')).toBe(true);
  });

  it('should set dark theme', () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme('dark');
    });

    expect(result.current.theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});

describe('useKeyboardShortcut', () => {
  it('should call callback on key press', () => {
    const callback = jest.fn();
    renderHook(() => useKeyboardShortcut('k', callback));

    act(() => {
      const event = new KeyboardEvent('keydown', { key: 'k' });
      window.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalled();
  });

  it('should call callback with ctrl modifier', () => {
    const callback = jest.fn();
    renderHook(() => useKeyboardShortcut('k', callback, { ctrl: true }));

    act(() => {
      const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
      window.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalled();
  });

  it('should not call callback without modifier when required', () => {
    const callback = jest.fn();
    renderHook(() => useKeyboardShortcut('k', callback, { ctrl: true }));

    act(() => {
      const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: false });
      window.dispatchEvent(event);
    });

    expect(callback).not.toHaveBeenCalled();
  });
});

describe('useInfiniteScroll', () => {
  it('should initialize with not fetching state', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useInfiniteScroll(callback));

    expect(result.current.isFetching).toBe(false);
  });

  it('should call callback when scrolling near bottom', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useInfiniteScroll(callback, { threshold: 100 }));

    Object.defineProperty(document.documentElement, 'scrollTop', {
      writable: true,
      configurable: true,
      value: 1000,
    });

    Object.defineProperty(document.documentElement, 'scrollHeight', {
      writable: true,
      configurable: true,
      value: 1200,
    });

    Object.defineProperty(document.documentElement, 'clientHeight', {
      writable: true,
      configurable: true,
      value: 200,
    });

    act(() => {
      const event = new Event('scroll');
      window.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalled();
  });
});
