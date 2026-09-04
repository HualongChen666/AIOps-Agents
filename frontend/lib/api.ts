import axios from 'axios';
import toast from 'react-hot-toast';

const instance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || '', // 使用空baseURL，让调用自己包含完整路径
  timeout: 15000,
});

function setCookie(name: string, value: string, days = 7) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function removeCookie(name: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  const token = localStorage.getItem('auth_token');
  if (token && token.trim()) return token.trim();
  const cookieToken = getCookie('auth_token');
  if (cookieToken && cookieToken.trim()) return cookieToken.trim();
  return null;
}

instance.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const internalKey = process.env.NEXT_PUBLIC_INTERNAL_API_KEY || localStorage.getItem('internal_key');
    if (internalKey && internalKey.trim()) {
      config.headers['X-Internal-Key'] = internalKey.trim();
    }
  }
  return config;
});

const PUBLIC_401_ENDPOINTS = ['/api/v1/auth/login', '/api/v1/auth/register-admin', '/api/v1/health/ping'];

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const method = error.config?.method?.toLowerCase() || '';
    const url = error.config?.url || '';

    if (error.response?.status === 401 && typeof window !== 'undefined') {
      const isPublicEndpoint = PUBLIC_401_ENDPOINTS.some((p) => url.endsWith(p));
      if (!isPublicEndpoint) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        removeCookie('auth_token');
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

export async function login(username: string, password: string) {
  const res = await instance.post('/api/v1/auth/login', { username, password });
  const { access_token, user } = res.data || {};
  if (access_token && typeof window !== 'undefined') {
    localStorage.setItem('auth_token', access_token);
    localStorage.setItem('user', JSON.stringify(user || {}));
    setCookie('auth_token', access_token);
  }
  return res.data;
}

export async function logout() {
  if (typeof window !== 'undefined') {
    try {
      await instance.post('/api/v1/auth/logout');
    } catch {
      // ignore: always clear local session even if server call fails
    }
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    removeCookie('auth_token');
    window.location.href = '/login';
  }
}

export async function getCurrentUser() {
  const res = await instance.get('/api/v1/auth/me');
  return res.data;
}

export function isAuthenticated() {
  if (typeof window === 'undefined') return false;
  return Boolean(getToken());
}

export default instance;
