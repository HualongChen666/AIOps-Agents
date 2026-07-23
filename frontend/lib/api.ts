// lib/api.ts – Axios 实例封装
import axios from 'axios';
import toast from 'react-hot-toast';

const instance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || '',
  timeout: 15000,
});

// 请求拦截 – 添加统一 Header（如 JWT）
instance.interceptors.request.use((config) => {
  // 示例：从 localStorage 中读取 token（如果有）
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截 – 统一错误弹 toast
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    toast.error(message);
    return Promise.reject(error);
  }
);

export default {
  get: instance.get,
  post: instance.post,
  put: instance.put,
  delete: instance.delete,
  patch: instance.patch,
};
