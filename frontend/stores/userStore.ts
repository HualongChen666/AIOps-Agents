import { create } from 'zustand';

interface User {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  created_at?: string;
}

interface UserState {
  currentUser: User | null;
  users: User[];
  isAuthenticated: boolean;
  setCurrentUser: (user: User | null) => void;
  setUsers: (users: User[]) => void;
  addUser: (user: User) => void;
  updateUser: (id: number, updates: Partial<User>) => void;
  deleteUser: (id: number) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  currentUser: null,
  users: [],
  isAuthenticated: false,
  setCurrentUser: (user) => set({ currentUser: user, isAuthenticated: !!user }),
  setUsers: (users) => set({ users }),
  addUser: (user) =>
    set((state) => ({
      users: [...state.users, user],
    })),
  updateUser: (id, updates) =>
    set((state) => ({
      users: state.users.map((user) =>
        user.id === id ? { ...user, ...updates } : user
      ),
    })),
  deleteUser: (id) =>
    set((state) => ({
      users: state.users.filter((user) => user.id !== id),
    })),
  logout: () => set({ currentUser: null, isAuthenticated: false }),
}));