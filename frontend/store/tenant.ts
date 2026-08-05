import { create } from 'zustand';

export interface Tenant {
  id: string;
  name: string;
  plan: 'free' | 'basic' | 'pro' | 'enterprise';
  status: 'active' | 'suspended' | 'expired';
  contact?: string;
  quota: {
    maxUsers: number;
    maxServices: number;
    maxAlerts: number;
    maxStorage: number; // GB
    cpu?: number;
    memory?: number;
    disk?: number;
  };
  usage: {
    users: number;
    services: number;
    alerts: number;
    storage: number; // GB
    cpu?: number;
    memory?: number;
    disk?: number;
  };
  billing: {
    cycle: 'monthly' | 'yearly';
    amount: number;
    currency: string;
    nextBillingDate: string;
  };
  created_at?: string;
}

interface TenantStore {
  currentTenant: Tenant | null;
  tenants: Tenant[];
  setCurrentTenant: (tenant: Tenant) => void;
  setTenants: (tenants: Tenant[]) => void;
  addTenant: (tenant: Tenant) => void;
  updateTenant: (id: string, updates: Partial<Tenant>) => void;
  removeTenant: (id: string) => void;
}

export const useTenantStore = create<TenantStore>((set) => ({
  currentTenant: null,
  tenants: [],
  setCurrentTenant: (tenant) => set({ currentTenant: tenant }),
  setTenants: (tenants) => set({ tenants }),
  addTenant: (tenant) => set((state) => ({ tenants: [...state.tenants, tenant] })),
  updateTenant: (id, updates) =>
    set((state) => ({
      tenants: state.tenants.map((t) => (t.id === id ? { ...t, ...updates } : t)),
      currentTenant: state.currentTenant?.id === id ? { ...state.currentTenant, ...updates } : state.currentTenant,
    })),
  removeTenant: (id) =>
    set((state) => ({
      tenants: state.tenants.filter((t) => t.id !== id),
      currentTenant: state.currentTenant?.id === id ? null : state.currentTenant,
    })),
}));
