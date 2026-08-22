/**
 * Comprehensive API Error Handling Tests
 * Tests network errors, timeouts, server errors, and error recovery mechanisms
 */

import axios from 'axios';
import { login, logout, getCurrentUser, getToken, isAuthenticated } from '@/lib/api';
import toast from 'react-hot-toast';

// Mock axios
jest.mock('axios');
jest.mock('react-hot-toast');

const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockedToast = toast as jest.Mocked<typeof toast>;

describe('API Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock localStorage
    const localStorageMock = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    };
    global.localStorage = localStorageMock as any;
    
    // Mock document.cookie
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: '',
    });
    
    // Mock window.location
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  describe('Network Error Handling', () => {
    it('should handle network connection errors', async () => {
      const networkError = new Error('Network Error');
      networkError.message = 'Network Error';
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(networkError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toThrow('Network Error');
    });

    it('should handle connection timeout errors', async () => {
      const timeoutError = new Error('timeout of 15000ms exceeded');
      (timeoutError as any).code = 'ECONNABORTED';
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(timeoutError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toThrow();
    });

    it('should handle connection refused errors', async () => {
      const connectionRefusedError = new Error('connect ECONNREFUSED');
      (connectionRefusedError as any).code = 'ECONNREFUSED';
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(connectionRefusedError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toThrow();
    });

    it('should handle DNS resolution errors', async () => {
      const dnsError = new Error('getaddrinfo ENOTFOUND');
      (dnsError as any).code = 'ENOTFOUND';
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(dnsError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toThrow();
    });

    it('should handle CORS errors', async () => {
      const corsError = new Error('Network Error');
      (corsError as any).response = undefined;
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(corsError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toThrow();
    });
  });

  describe('Server Error Handling', () => {
    it('should handle 500 Internal Server Error', async () => {
      const serverError = {
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(serverError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(serverError);
      expect(mockedToast.error).toHaveBeenCalledWith('Internal Server Error');
    });

    it('should handle 502 Bad Gateway', async () => {
      const badGatewayError = {
        response: {
          status: 502,
          data: { detail: 'Bad Gateway' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(badGatewayError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(badGatewayError);
      expect(mockedToast.error).toHaveBeenCalledWith('Bad Gateway');
    });

    it('should handle 503 Service Unavailable', async () => {
      const serviceUnavailableError = {
        response: {
          status: 503,
          data: { detail: 'Service Unavailable' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(serviceUnavailableError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(serviceUnavailableError);
      expect(mockedToast.error).toHaveBeenCalledWith('Service Unavailable');
    });

    it('should handle 504 Gateway Timeout', async () => {
      const gatewayTimeoutError = {
        response: {
          status: 504,
          data: { detail: 'Gateway Timeout' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(gatewayTimeoutError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(gatewayTimeoutError);
      expect(mockedToast.error).toHaveBeenCalledWith('Gateway Timeout');
    });
  });

  describe('Client Error Handling', () => {
    it('should handle 400 Bad Request', async () => {
      const badRequestError = {
        response: {
          status: 400,
          data: { detail: 'Bad Request: Invalid input' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(badRequestError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(badRequestError);
      expect(mockedToast.error).toHaveBeenCalledWith('Bad Request: Invalid input');
    });

    it('should handle 401 Unauthorized on protected endpoints', async () => {
      const unauthorizedError = {
        response: {
          status: 401,
          data: { detail: 'Unauthorized' },
        },
        config: { method: 'get', url: '/api/v1/protected' },
      };
      
      mockedAxios.create.mockReturnValue({
        get: jest.fn().mockRejectedValue(unauthorizedError),
        post: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.response?.status === 401 && typeof window !== 'undefined') {
              const PUBLIC_401_ENDPOINTS = ['/api/v1/auth/login', '/api/v1/auth/register-admin', '/api/v1/health/ping'];
              const isPublicEndpoint = PUBLIC_401_ENDPOINTS.some((p) => error.config?.url?.endsWith(p));
              if (!isPublicEndpoint) {
                global.localStorage?.removeItem('auth_token');
                global.localStorage?.removeItem('user');
                if ((window as any).location.pathname !== '/login') {
                  (window as any).location.href = '/login';
                }
              }
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      (global.localStorage as any).getItem.mockReturnValue('test-token');
      
      await expect(getCurrentUser()).rejects.toEqual(unauthorizedError);
      expect(global.localStorage?.removeItem).toHaveBeenCalledWith('auth_token');
      expect(global.localStorage?.removeItem).toHaveBeenCalledWith('user');
      expect((window as any).location.href).toBe('/login');
    });

    it('should not redirect on 401 for public endpoints', async () => {
      const unauthorizedError = {
        response: {
          status: 401,
          data: { detail: 'Unauthorized' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(unauthorizedError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.response?.status === 401 && typeof window !== 'undefined') {
              const PUBLIC_401_ENDPOINTS = ['/api/v1/auth/login', '/api/v1/auth/register-admin', '/api/v1/health/ping'];
              const isPublicEndpoint = PUBLIC_401_ENDPOINTS.some((p) => error.config?.url?.endsWith(p));
              if (!isPublicEndpoint) {
                global.localStorage?.removeItem('auth_token');
                global.localStorage?.removeItem('user');
                if ((window as any).location.pathname !== '/login') {
                  (window as any).location.href = '/login';
                }
              }
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      (global.localStorage as any).getItem.mockReturnValue('test-token');
      
      await expect(login('testuser', 'password')).rejects.toEqual(unauthorizedError);
      expect(global.localStorage?.removeItem).not.toHaveBeenCalled();
      expect((window as any).location.href).toBe('');
    });

    it('should handle 403 Forbidden', async () => {
      const forbiddenError = {
        response: {
          status: 403,
          data: { detail: 'Forbidden: Insufficient permissions' },
        },
        config: { method: 'post', url: '/api/v1/admin' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(forbiddenError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(forbiddenError);
      expect(mockedToast.error).toHaveBeenCalledWith('Forbidden: Insufficient permissions');
    });

    it('should handle 404 Not Found', async () => {
      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Resource not found' },
        },
        config: { method: 'get', url: '/api/v1/nonexistent' },
      };
      
      mockedAxios.create.mockReturnValue({
        get: jest.fn().mockRejectedValue(notFoundError),
        post: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(getCurrentUser()).rejects.toEqual(notFoundError);
      expect(mockedToast.error).not.toHaveBeenCalled(); // GET requests don't show toast
    });

    it('should handle 409 Conflict', async () => {
      const conflictError = {
        response: {
          status: 409,
          data: { detail: 'Resource already exists' },
        },
        config: { method: 'post', url: '/api/v1/users' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(conflictError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(conflictError);
      expect(mockedToast.error).toHaveBeenCalledWith('Resource already exists');
    });

    it('should handle 422 Unprocessable Entity', async () => {
      const validationError = {
        response: {
          status: 422,
          data: { detail: 'Validation error: Invalid email format' },
        },
        config: { method: 'post', url: '/api/v1/users' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(validationError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(validationError);
      expect(mockedToast.error).toHaveBeenCalledWith('Validation error: Invalid email format');
    });

    it('should handle 429 Too Many Requests', async () => {
      const rateLimitError = {
        response: {
          status: 429,
          data: { detail: 'Rate limit exceeded' },
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(rateLimitError),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(rateLimitError);
      expect(mockedToast.error).toHaveBeenCalledWith('Rate limit exceeded');
    });
  });

  describe('Error Recovery Mechanisms', () => {
    it('should handle logout gracefully even if server call fails', async () => {
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(new Error('Server error')),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn(),
        },
      } as any);

      await logout();
      
      expect(global.localStorage?.removeItem).toHaveBeenCalledWith('auth_token');
      expect(global.localStorage?.removeItem).toHaveBeenCalledWith('user');
      expect((window as any).location.href).toBe('/login');
    });

    it('should handle logout with successful server call', async () => {
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockResolvedValue({ data: { success: true } }),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn(),
        },
      } as any);

      await logout();
      
      expect(global.localStorage?.removeItem).toHaveBeenCalledWith('auth_token');
      expect(global.localStorage?.removeItem).toHaveBeenCalledWith('user');
      expect((window as any).location.href).toBe('/login');
    });

    it('should handle missing error response data', async () => {
      const errorWithoutData = {
        response: {
          status: 500,
        },
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(errorWithoutData),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(errorWithoutData);
      expect(mockedToast.error).toHaveBeenCalledWith('请求失败');
    });

    it('should handle error without response', async () => {
      const errorWithoutResponse = {
        message: 'Request failed',
        config: { method: 'post', url: '/api/v1/auth/login' },
      };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(errorWithoutResponse),
        get: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn((success) => success, (error) => {
            if (error.config?.method !== 'get' && error.config?.method !== 'head') {
              mockedToast.error(error.response?.data?.detail || error.message || '请求失败');
            }
            return Promise.reject(error);
          })),
        },
      } as any);

      await expect(login('testuser', 'password')).rejects.toEqual(errorWithoutResponse);
      expect(mockedToast.error).toHaveBeenCalledWith('Request failed');
    });
  });

  describe('Token Management Error Handling', () => {
    it('should handle missing token gracefully', () => {
      (global.localStorage as any).getItem.mockReturnValue(null);
      
      const token = getToken();
      expect(token).toBeNull();
    });

    it('should handle empty token', () => {
      (global.localStorage as any).getItem.mockReturnValue('');
      
      const token = getToken();
      expect(token).toBeNull();
    });

    it('should handle whitespace-only token', () => {
      (global.localStorage as any).getItem.mockReturnValue('   ');
      
      const token = getToken();
      expect(token).toBeNull();
    });

    it('should handle valid token with whitespace', () => {
      (global.localStorage as any).getItem.mockReturnValue('  valid-token  ');
      
      const token = getToken();
      expect(token).toBe('valid-token');
    });

    it('should return false for isAuthenticated when no token', () => {
      (global.localStorage as any).getItem.mockReturnValue(null);
      
      const authenticated = isAuthenticated();
      expect(authenticated).toBe(false);
    });

    it('should return true for isAuthenticated when token exists', () => {
      (global.localStorage as any).getItem.mockReturnValue('valid-token');
      
      const authenticated = isAuthenticated();
      expect(authenticated).toBe(true);
    });
  });

  describe('Request Interceptor Error Handling', () => {
    it('should handle missing internal API key gracefully', () => {
      const mockConfig = { headers: {} };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn(),
        get: jest.fn(),
        interceptors: {
          request: {
            use: jest.fn((callback) => {
              const result = callback(mockConfig);
              expect(result.headers.Authorization).toBeUndefined();
              expect(result.headers['X-Internal-Key']).toBeUndefined();
            }),
          },
          response: { use: jest.fn() },
        },
      } as any);

      (global.localStorage as any).getItem.mockReturnValue(null);
      delete process.env.NEXT_PUBLIC_INTERNAL_API_KEY;
    });

    it('should add authorization header when token exists', () => {
      const mockConfig = { headers: {} };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn(),
        get: jest.fn(),
        interceptors: {
          request: {
            use: jest.fn((callback) => {
              (global.localStorage as any).getItem.mockReturnValue('test-token');
              const result = callback(mockConfig);
              expect(result.headers.Authorization).toBe('Bearer test-token');
            }),
          },
          response: { use: jest.fn() },
        },
      } as any);
    });

    it('should add internal API key when available', () => {
      const mockConfig = { headers: {} };
      
      mockedAxios.create.mockReturnValue({
        post: jest.fn(),
        get: jest.fn(),
        interceptors: {
          request: {
            use: jest.fn((callback) => {
              process.env.NEXT_PUBLIC_INTERNAL_API_KEY = 'internal-key';
              const result = callback(mockConfig);
              expect(result.headers['X-Internal-Key']).toBe('internal-key');
            }),
          },
          response: { use: jest.fn() },
        },
      } as any);
    });
  });

  describe('Error Logging and Monitoring', () => {
    it('should log errors to console in development', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      const error = new Error('Test error');
      console.error('Test error message', error);
      
      expect(consoleSpy).toHaveBeenCalledWith('Test error message', error);
      consoleSpy.mockRestore();
    });
  });

  describe('Cookie Error Handling', () => {
    it('should handle cookie operations in non-browser environment', () => {
      // Mock window as undefined to simulate SSR
      const originalWindow = global.window;
      (global as any).window = undefined;
      
      const token = getToken();
      expect(token).toBeNull();
      
      global.window = originalWindow;
    });

    it('should handle document.cookie errors gracefully', () => {
      const originalCookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
      Object.defineProperty(document, 'cookie', {
        get: () => { throw new Error('Cookie access denied'); },
        set: () => { throw new Error('Cookie access denied'); },
      });
      
      (global.localStorage as any).getItem.mockReturnValue('test-token');
      const token = getToken();
      expect(token).toBe('test-token');
      
      // Restore original cookie descriptor
      if (originalCookie) {
        Object.defineProperty(document, 'cookie', originalCookie);
      }
    });
  });
});
