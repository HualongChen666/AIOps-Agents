import api, { login, logout, getCurrentUser, isAuthenticated, getStoredUser } from '@/lib/api';
import axios from 'axios';

// Mock axios. `lib/api.ts` runs `axios.create(...)` at import time and then
// registers interceptors on the result, so the auto-mock (which returns
// undefined) makes the whole suite fail to load. Provide a functional stub.
jest.mock('axios', () => {
  const interceptors = {
    request: { use: jest.fn((cb: any) => cb) },
    response: { use: jest.fn((ok: any, err: any) => ({ ok, err })) },
  };
  const instance: any = {
    interceptors,
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
  };
  const create = jest.fn(() => instance);
  return { __esModule: true, default: { create }, create };
});
jest.mock('react-hot-toast');

const mockInstance: any = (require('axios') as any).create.mock.results[0]?.value;
const createConfig: any = (require('axios') as any).create.mock.calls[0]?.[0];
const registeredErrorInterceptor: any =
  mockInstance?.interceptors?.response?.use?.mock?.calls?.[0]?.[1];

describe('API Module', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('API Instance Configuration', () => {
    it('should create axios instance with default config', () => {
      expect(createConfig).toEqual({
        baseURL: process.env.NEXT_PUBLIC_API_BASE || '',
        timeout: 15000,
        withCredentials: true,
      });
    });

    it('should send credentials (HttpOnly session cookie) with every request', () => {
      expect(createConfig.withCredentials).toBe(true);
    });
  });

  describe('Session storage', () => {
    it('never persists the access token in localStorage', async () => {
      (api.request as jest.Mock).mockResolvedValue({
        data: { access_token: 'new-token', user: { id: 1, username: 'test' } },
      });

      await login('testuser', 'password');

      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    it('never writes the access token to a JavaScript-readable cookie', async () => {
      (api.request as jest.Mock).mockResolvedValue({
        data: { access_token: 'new-token', user: { id: 1, username: 'test' } },
      });

      await login('testuser', 'password');

      expect(document.cookie).not.toContain('auth_token');
    });

    it('stores only the non-sensitive user profile', async () => {
      (api.request as jest.Mock).mockResolvedValue({
        data: { access_token: 'new-token', user: { id: 1, username: 'test' } },
      });

      await login('testuser', 'password');

      expect(getStoredUser()).toEqual({ id: 1, username: 'test' });
    });
  });

  describe('Authentication Status', () => {
    it('should return true when a session marker exists', () => {
      localStorage.setItem('user', JSON.stringify({ id: 1 }));
      expect(isAuthenticated()).toBe(true);
    });

    it('should return false when no session marker exists', () => {
      expect(isAuthenticated()).toBe(false);
    });

    it('should return false when the session marker is not valid JSON', () => {
      localStorage.setItem('user', 'not-json');
      expect(isAuthenticated()).toBe(false);
    });
  });

  describe('Login Function', () => {
    it('should call login API with credentials', async () => {
      (api.request as jest.Mock).mockResolvedValue({
        data: { access_token: 'new-token', user: { id: 1, username: 'test' } },
      });

      await login('testuser', 'password');

      expect(api.request).toHaveBeenCalledWith({
        method: 'POST',
        url: '/api/v1/auth/login',
        data: { username: 'testuser', password: 'password' },
      });
    });

    it('should tolerate a response without a user object', async () => {
      (api.request as jest.Mock).mockResolvedValue({ data: { access_token: 'new-token' } });

      await login('testuser', 'password');

      expect(localStorage.getItem('user')).toBe(JSON.stringify({}));
      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    it('should tolerate a null response body', async () => {
      (api.request as jest.Mock).mockResolvedValue({ data: null });

      await login('testuser', 'password');

      expect(localStorage.getItem('auth_token')).toBeNull();
    });
  });

  describe('Logout Function', () => {
    it('should call logout API', async () => {
      (api.post as jest.Mock).mockResolvedValue({ data: {} });

      await logout();

      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/logout');
    });

    it('should remove the stored user on logout', async () => {
      localStorage.setItem('user', JSON.stringify({ id: 1 }));
      (api.post as jest.Mock).mockResolvedValue({ data: {} });

      await logout();

      expect(localStorage.getItem('user')).toBeNull();
      expect(isAuthenticated()).toBe(false);
    });

    it('should clear local state even when the API call fails', async () => {
      localStorage.setItem('user', JSON.stringify({ id: 1 }));
      (api.post as jest.Mock).mockRejectedValue(new Error('API Error'));

      await logout();

      expect(isAuthenticated()).toBe(false);
    });
  });

  describe('Get Current User Function', () => {
    it('should call user API', async () => {
      (api.get as jest.Mock).mockResolvedValue({ data: { id: 1, username: 'test' } });

      await getCurrentUser();

      expect(api.get).toHaveBeenCalledWith('/api/v1/auth/me');
    });

    it('should return user data', async () => {
      (api.get as jest.Mock).mockResolvedValue({ data: { id: 1, username: 'test' } });

      expect(await getCurrentUser()).toEqual({ id: 1, username: 'test' });
    });
  });

  describe('No internal key in the browser', () => {
    it('does not inline an internal API key into the client bundle', () => {
      expect(process.env.NEXT_PUBLIC_INTERNAL_API_KEY).toBeUndefined();
    });
  });

  describe('Response Interceptor', () => {
    it('should clear the session when the real 401 interceptor runs on a protected endpoint', async () => {
      const errorHandler = registeredErrorInterceptor;
      localStorage.setItem('user', JSON.stringify({ id: 1 }));
      const mockError = {
        response: { status: 401 },
        config: { method: 'get', url: '/api/v1/protected' },
      };

      await expect(errorHandler(mockError)).rejects.toEqual(mockError);

      expect(localStorage.getItem('user')).toBeNull();
      expect(isAuthenticated()).toBe(false);
    });

    it('should keep the session for public 401 endpoints (e.g. failed login)', async () => {
      const errorHandler = registeredErrorInterceptor;
      localStorage.setItem('user', JSON.stringify({ id: 1 }));
      const mockError = {
        response: { status: 401 },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };

      await expect(errorHandler(mockError)).rejects.toEqual(mockError);

      expect(localStorage.getItem('user')).not.toBeNull();
    });
  });
});
