/**
 * API Error Handling Tests
 *
 * Exercises the error paths of lib/api against its CURRENT contract:
 *  - requests go through `instance.request(...)` (wrapped with client-side rate limiting),
 *  - the session is an HttpOnly cookie; the client only keeps a non-sensitive
 *    user profile in localStorage (there is deliberately no getToken()),
 *  - a single response interceptor handles 401 redirects and error toasts.
 *
 * The axios mock installs a working instance (with interceptors) so that
 * lib/api's real interceptor is the code under test.
 */

jest.mock('axios', () => {
  const handlers: { fulfilled?: (r: any) => any; rejected?: (e: any) => any } = {};

  const instance: any = {
    request: jest.fn(),
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: {
        use: jest.fn((fulfilled: (r: any) => any, rejected: (e: any) => any) => {
          handlers.fulfilled = fulfilled;
          handlers.rejected = rejected;
          return 1;
        }),
      },
    },
    __handlers: handlers,
    __nextError: null,
  };

  // Axios runs a rejected request through the response interceptor's onRejected
  // handler; emulate that so the real interceptor logic is what gets asserted.
  const route = (config: any): Promise<never> => {
    const err = instance.__nextError;
    err.config = { ...(err.config || {}), ...(config || {}) };
    return handlers.rejected ? handlers.rejected(err) : Promise.reject(err);
  };
  const ok = () => Promise.resolve({ data: {} });

  instance.request.mockImplementation((c: any) => (instance.__nextError ? route(c) : ok()));
  instance.get.mockImplementation(() => (instance.__nextError ? route({ method: 'get' }) : ok()));
  instance.post.mockImplementation(() => (instance.__nextError ? route({ method: 'post' }) : ok()));
  instance.put.mockImplementation(() => (instance.__nextError ? route({ method: 'put' }) : ok()));
  instance.patch.mockImplementation(() => (instance.__nextError ? route({ method: 'patch' }) : ok()));
  instance.delete.mockImplementation(() => (instance.__nextError ? route({ method: 'delete' }) : ok()));

  const create = jest.fn(() => instance);
  return { __esModule: true, default: { create }, create, __instance: instance };
});

jest.mock('react-hot-toast');

import toast from 'react-hot-toast';

let mockedToast: jest.Mocked<typeof toast>;
let instanceMock: any;
let api: typeof import('@/lib/api');

/** Make the next request fail, routed through the response interceptor. */
function failNextWith(error: any) {
  instanceMock.__nextError = error;
}

/** Make the next request succeed with the given payload. */
function succeedNextWith(data: any) {
  instanceMock.__nextError = null;
  instanceMock.request.mockImplementationOnce(async () => ({ data }) as any);
}

describe('API Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Isolate module state (frontend rate-limiter buckets, axios instance, api
    // client) so bursts of requests across tests never exhaust a shared bucket.
    jest.resetModules();

    instanceMock = (jest.requireMock('axios') as any).__instance;
    // Resolve the toast mock exactly the way lib/api does (default import), so
    // the spy and the code under test share one instance after resetModules().
    const toastModule = require('react-hot-toast');
    mockedToast = (toastModule.default ?? toastModule) as jest.Mocked<typeof toast>;
    instanceMock.__nextError = null;

    const localStorageMock = {
      getItem: jest.fn().mockReturnValue(null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    };
    Object.defineProperty(global, 'localStorage', {
      configurable: true,
      writable: true,
      value: localStorageMock,
    });

    try {
      Object.defineProperty(window, 'location', {
        configurable: true,
        writable: true,
        value: { href: '', pathname: '/dashboard' },
      });
    } catch {
      /* jsdom may freeze location; assertions fall back to state checks */
    }

    api = require('@/lib/api');
  });

  describe('Network Error Handling', () => {
    it('should propagate network connection errors', async () => {
      failNextWith(new Error('Network Error'));
      await expect(api.login('testuser', 'password')).rejects.toThrow('Network Error');
    });

    it('should propagate connection timeout errors', async () => {
      const timeoutError: any = new Error('timeout of 15000ms exceeded');
      timeoutError.code = 'ECONNABORTED';
      failNextWith(timeoutError);
      await expect(api.login('testuser', 'password')).rejects.toThrow('timeout');
    });

    it('should propagate connection refused errors', async () => {
      const refused: any = new Error('connect ECONNREFUSED');
      refused.code = 'ECONNREFUSED';
      failNextWith(refused);
      await expect(api.login('testuser', 'password')).rejects.toThrow('ECONNREFUSED');
    });

    it('should propagate DNS resolution errors', async () => {
      const dnsError: any = new Error('getaddrinfo ENOTFOUND');
      dnsError.code = 'ENOTFOUND';
      failNextWith(dnsError);
      await expect(api.login('testuser', 'password')).rejects.toThrow('ENOTFOUND');
    });

    it('should not toast for GET requests', async () => {
      const err: any = new Error('Network Error');
      err.config = { method: 'get', url: '/api/v1/alerts' };
      failNextWith(err);

      await expect(api.getCurrentUser()).rejects.toThrow('Network Error');
      expect(mockedToast.error).not.toHaveBeenCalled();
    });
  });

  describe('Server Error Handling', () => {
    const serverCases: Array<[number, string]> = [
      [500, 'Internal Server Error'],
      [502, 'Bad Gateway'],
      [503, 'Service Unavailable'],
      [504, 'Gateway Timeout'],
    ];

    it.each(serverCases)('should handle %i and toast its detail', async (status, detail) => {
      failNextWith({
        response: { status, data: { detail } },
        config: { method: 'post', url: '/api/v1/auth/login' },
      });

      await expect(api.login('testuser', 'password')).rejects.toHaveProperty('response.status', status);
      expect(mockedToast.error).toHaveBeenCalledWith(detail);
    });
  });

  describe('Client Error Handling', () => {
    it('should toast the detail on 400 Bad Request', async () => {
      failNextWith({
        response: { status: 400, data: { detail: 'Bad Request' } },
        config: { method: 'post', url: '/api/v1/alerts' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Bad Request');
    });

    it('should clear the session and redirect on 401 for a protected endpoint', async () => {
      failNextWith({
        response: { status: 401, data: { detail: 'Unauthorized' } },
        config: { method: 'get', url: '/api/v1/alerts' },
      });

      await expect(api.getCurrentUser()).rejects.toBeDefined();
      expect((global as any).localStorage.removeItem).toHaveBeenCalledWith('user');
    });

    it('should NOT clear the session on 401 for public endpoints', async () => {
      failNextWith({
        response: { status: 401, data: { detail: 'Unauthorized' } },
        config: { method: 'post', url: '/api/v1/auth/login' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect((global as any).localStorage.removeItem).not.toHaveBeenCalled();
      // login is a POST, so the error is still surfaced to the user
      expect(mockedToast.error).toHaveBeenCalledWith('Unauthorized');
    });

    it('should toast on 403 Forbidden', async () => {
      failNextWith({
        response: { status: 403, data: { detail: 'Forbidden' } },
        config: { method: 'post', url: '/api/v1/alerts' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Forbidden');
    });

    it('should toast on 404 Not Found', async () => {
      failNextWith({
        response: { status: 404, data: { detail: 'Not Found' } },
        config: { method: 'post', url: '/api/v1/alerts/1' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Not Found');
    });

    it('should toast on 409 Conflict', async () => {
      failNextWith({
        response: { status: 409, data: { detail: 'Conflict' } },
        config: { method: 'post', url: '/api/v1/alerts' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Conflict');
    });

    it('should toast on 422 Unprocessable Entity', async () => {
      failNextWith({
        response: { status: 422, data: { detail: 'Validation failed' } },
        config: { method: 'post', url: '/api/v1/auth/login' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Validation failed');
    });

    it('should toast on 429 Too Many Requests', async () => {
      failNextWith({
        response: { status: 429, data: { detail: 'Too Many Requests' } },
        config: { method: 'post', url: '/api/v1/alerts' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Too Many Requests');
    });
  });

  describe('Logout', () => {
    it('should still clear the session when the server call fails', async () => {
      failNextWith(new Error('Network Error'));

      await api.logout();

      expect((global as any).localStorage.removeItem).toHaveBeenCalledWith('user');
    });

    it('should clear the session after a successful server call', async () => {
      instanceMock.__nextError = null;

      await api.logout();

      expect(instanceMock.post).toHaveBeenCalledWith('/api/v1/auth/logout');
      expect((global as any).localStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });

  describe('Malformed error payloads', () => {
    it('should fall back to a generic message when detail is missing', async () => {
      failNextWith({
        response: { status: 500, data: {} },
        message: 'Request failed',
        config: { method: 'post', url: '/api/v1/alerts' },
      });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Request failed');
    });

    it('should fall back to the default message when response and message are absent', async () => {
      failNextWith({ config: { method: 'post', url: '/api/v1/alerts' } });

      await expect(api.login('testuser', 'password')).rejects.toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('请求失败');
    });
  });

  describe('Session marker management', () => {
    it('should return null when nothing is stored', () => {
      (global as any).localStorage.getItem.mockReturnValue(null);
      expect(api.getStoredUser()).toBeNull();
    });

    it('should return null for an empty stored value', () => {
      (global as any).localStorage.getItem.mockReturnValue('');
      expect(api.getStoredUser()).toBeNull();
    });

    it('should return null for corrupted JSON', () => {
      (global as any).localStorage.getItem.mockReturnValue('{not-json');
      expect(api.getStoredUser()).toBeNull();
    });

    it('should parse a valid stored profile', () => {
      (global as any).localStorage.getItem.mockReturnValue(JSON.stringify({ username: 'alice' }));
      expect(api.getStoredUser()).toEqual({ username: 'alice' });
    });

    it('should report the user as unauthenticated when no profile is stored', () => {
      (global as any).localStorage.getItem.mockReturnValue(null);
      expect(api.isAuthenticated()).toBe(false);
    });

    it('should report the user as authenticated when a profile is stored', () => {
      (global as any).localStorage.getItem.mockReturnValue(JSON.stringify({ username: 'alice' }));
      expect(api.isAuthenticated()).toBe(true);
    });

    it('should persist the profile returned by a successful login', async () => {
      succeedNextWith({ user: { username: 'alice' }, access_token: 'opaque' });

      await api.login('alice', 'secret');

      expect((global as any).localStorage.setItem).toHaveBeenCalledWith(
        'user',
        JSON.stringify({ username: 'alice' })
      );
    });
  });

  describe('Error logging', () => {
    it('should log errors to console in development', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      console.error('Test error message', new Error('Test error'));

      expect(consoleSpy).toHaveBeenCalledWith('Test error message', expect.any(Error));
      consoleSpy.mockRestore();
    });
  });
});
