import { create } from 'zustand';

interface User {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
}

interface DashboardState {
  metrics: {
    cpu: number;
    memory: number;
    disk: number;
  };
  alerts: number;
  repairs: number;
  lastUpdate: Date | null;
  setMetrics: (metrics: Partial<DashboardState['metrics']>) => void;
  setAlerts: (count: number) => void;
  setRepairs: (count: number) => void;
  updateLastUpdate: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  metrics: {
    cpu: 0,
    memory: 0,
    disk: 0,
  },
  alerts: 0,
  repairs: 0,
  lastUpdate: null,
  setMetrics: (metrics) =>
    set((state) => ({
      metrics: { ...state.metrics, ...metrics },
    })),
  setAlerts: (count) => set({ alerts: count }),
  setRepairs: (count) => set({ repairs: count }),
  updateLastUpdate: () => set({ lastUpdate: new Date() }),
}));
