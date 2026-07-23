import { create } from 'zustand';

interface Tenant {
  id: string;
  name: string;
  plan: 'free' | 'basic' | 'pro' | 'enterprise';
  status: 'active' | 'suspended' | 'expired';
  quota: {
    maxUsers: number;
    maxServices: number;
    maxAlerts: number;
    maxStorage: number; // GB
  };
  usage: {
    users: number;
    services: number;
    alerts: number;
    storage: number; // GB
  };
  billing: {
    cycle: 'monthly' | 'yearly';
    amount: number;
    currency: string;
    nextBillingDate: string;
  };
}

interface TenantStore {
  currentTenant: Tenant | null;
  tenants: Tenant[];
  setCurrentTenant: (tenant: Tenant) => void;
  addTenant: (tenant: Tenant) => void;
  updateTenant: (id: string, updates: Partial<Tenant>) => void;
  removeTenant: (id: string) => void;
}

export const useTenantStore = create<TenantStore>((set) => ({
  currentTenant: null,
  tenants: [
    {
      id: 'tenant-001',
      name: 'Production',
      plan: 'enterprise',
      status: 'active',
      quota: {
        maxUsers: 100,
        maxServices: 50,
        maxAlerts: 10000,
        maxStorage: 1000,
      },
      usage: {
        users: 45,
        services: 23,
        alerts: 3200,
        storage: 450,
      },
      billing: {
        cycle: 'monthly',
        amount: 5000,
        currency: 'CNY',
        nextBillingDate: '2024-07-01',
      },
    },
    {
      id: 'tenant-002',
      name: 'Staging',
      plan: 'pro',
      status: 'active',
      quota: {
        maxUsers: 50,
        maxServices: 25,
        maxAlerts: 5000,
        maxStorage: 500,
      },
      usage: {
        users: 12,
        services: 8,
        alerts: 850,
        storage: 120,
      },
      billing: {
        cycle: 'monthly',
        amount: 2000,
        currency: 'CNY',
        nextBillingDate: '2024-07-01',
      },
    },
    {
      id: 'tenant-003',
      name: 'Development',
      plan: 'basic',
      status: 'active',
      quota: {
        maxUsers: 10,
        maxServices: 5,
        maxAlerts: 1000,
        maxStorage: 100,
      },
      usage: {
        users: 5,
        services: 3,
        alerts: 200,
        storage: 30,
      },
      billing: {
        cycle: 'monthly',
        amount: 500,
        currency: 'CNY',
        nextBillingDate: '2024-07-01',
      },
    },
  ],
  setCurrentTenant: (tenant) => set({ currentTenant: tenant }),
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
