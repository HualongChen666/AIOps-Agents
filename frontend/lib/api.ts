import axios from 'axios';
import toast from 'react-hot-toast';

const instance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:3000',
  timeout: 15000,
});

instance.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token && token.trim()) {
      config.headers.Authorization = `Bearer ${token.trim()}`;
    }
    const internalKey = process.env.NEXT_PUBLIC_INTERNAL_API_KEY || localStorage.getItem('internal_key');
    if (internalKey && internalKey.trim()) {
      config.headers['X-Internal-Key'] = internalKey.trim();
    }
  }
  return config;
});

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const method = error.config?.method?.toLowerCase() || '';

    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
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
  }
  return res.data;
}

export function logout() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }
}

export async function getCurrentUser() {
  const res = await instance.get('/api/v1/auth/me');
  return res.data;
}

export function isAuthenticated() {
  if (typeof window === 'undefined') return false;
  const token = localStorage.getItem('auth_token');
  return Boolean(token && token.trim());
}

export default instance;
