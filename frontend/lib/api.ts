import axios, { type AxiosResponse } from 'axios';
import toast from 'react-hot-toast';
import { withRateLimit } from '@/lib/rateLimiter';

const instance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || '', // 使用空baseURL，让调用自己包含完整路径
  timeout: 15000,
  // Send the HttpOnly session cookie with every request (same-origin by default
  // via the /api rewrite; explicit for deployments with a different API origin).
  withCredentials: true,
});

// ---------------------------------------------------------------------------
// Session storage
//
// The access token lives exclusively in an HttpOnly cookie issued by
// `POST /api/v1/auth/login`; JavaScript can never read it, so an XSS cannot
// exfiltrate credentials. Only the non-sensitive user profile is kept locally,
// and it is used purely as a client-side routing marker — every API call is
// authorised server-side by the cookie.
// ---------------------------------------------------------------------------
const USER_KEY = 'user';

export function getStoredUser(): Record<string, unknown> | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setStoredUser(user: unknown) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}));
}

function clearStoredUser() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(USER_KEY);
}

const PUBLIC_401_ENDPOINTS = ['/api/v1/auth/login', '/api/v1/auth/register-admin', '/api/v1/health/ping'];

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const method = error.config?.method?.toLowerCase() || '';
    const url = error.config?.url || '';

    if (error.response?.status === 401 && typeof window !== 'undefined') {
      const isPublicEndpoint = PUBLIC_401_ENDPOINTS.some((p) => url.endsWith(p));
      if (!isPublicEndpoint) {
        clearStoredUser();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }

    if (method && method !== 'get' && method !== 'head') {
      const message = error.response?.data?.detail || error.message || '请求失败';
      toast.error(message);
    }
    return Promise.reject(error);
  }
);

// Generic request wrapper applying rate limiting per endpoint.
// NOTE: the return type is the axios response (not the unwrapped payload), which
// is what every caller destructures via `response.data`.
async function requestWithRateLimit<T>(
  method: string,
  url: string,
  data?: any
): Promise<AxiosResponse<T>> {
  const key = `${method.toUpperCase()}_${url}`;
  return withRateLimit(key, () => instance.request<T>({ method, url, data }));
}

export async function login(username: string, password: string) {
  const response = await requestWithRateLimit<any>('POST', '/api/v1/auth/login', { username, password });
  const { user } = response.data || {};
  // The access token is NOT stored: the server has already set it as an
  // HttpOnly cookie in this same response.
  setStoredUser(user);
  return response.data;
}

export async function logout() {
  if (typeof window !== 'undefined') {
    try {
      // Clears the HttpOnly cookie and blacklists the JWT server-side.
      await instance.post('/api/v1/auth/logout');
    } catch {
      // ignore: always clear the local session even if the server call fails
    }
    clearStoredUser();
    window.location.href = '/login';
  }
}

export async function getCurrentUser() {
  const res = await instance.get('/api/v1/auth/me');
  return res.data;
}

export function isAuthenticated() {
  if (typeof window === 'undefined') return false;
  return getStoredUser() !== null;
}

export default instance;
