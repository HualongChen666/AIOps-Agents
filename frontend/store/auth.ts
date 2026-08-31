import { create } from 'zustand';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user' | 'viewer';
  permissions: string[];
}

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  isAuthenticated: false,
  
  setUser: (user) => {
    set({ user, isAuthenticated: !!user });
    if (user && typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(user));
    } else if (user === null && typeof window !== 'undefined') {
      localStorage.removeItem('user');
    }
  },
  
  logout: () => {
    set({ user: null, isAuthenticated: false });
    if (typeof window !== 'undefined') {
      localStorage.removeItem('user');
      localStorage.removeItem('auth_token');
    }
  },
  
  hasPermission: (permission) => {
    const { user } = get();
    if (!user) return false;
    if (user.role === 'admin') return true;
    return user.permissions.includes(permission);
  },
  
  hasRole: (role) => {
    const { user } = get();
    if (!user) return false;
    return user.role === role;
  },
}));

// Initialize from localStorage if available
if (typeof window !== 'undefined') {
  const storedUser = localStorage.getItem('user');
  if (storedUser) {
    try {
      const user = JSON.parse(storedUser);
      useAuthStore.setState({ user, isAuthenticated: true });
    } catch (error) {
      console.error('Failed to parse stored user:', error);
    }
  }
}
