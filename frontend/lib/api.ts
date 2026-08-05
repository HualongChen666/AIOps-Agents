import axios from 'axios';
import toast from 'react-hot-toast';

const instance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000',
  timeout: 15000,
});

instance.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const internalKey = process.env.NEXT_PUBLIC_INTERNAL_API_KEY || localStorage.getItem('internal_key');
    if (internalKey) {
      config.headers['X-Internal-Key'] = internalKey;
    }
  }
  return config;
});

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    toast.error(message);
    return Promise.reject(error);
  }
);

export default instance;
