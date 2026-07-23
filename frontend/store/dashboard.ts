import { create } from 'zustand';

interface DashboardStats {
  alertCount: number;
  healSuccessRate: number;
  mttr: number;
  availability: number;
}

interface DashboardStore {
  stats: DashboardStats;
  setStats: (stats: DashboardStats) => void;
  updateStat: (key: keyof DashboardStats, value: number) => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  stats: {
    alertCount: 0,
    healSuccessRate: 0,
    mttr: 0,
    availability: 0,
  },
  setStats: (stats) => set({ stats }),
  updateStat: (key, value) =>
    set((state) => ({
      stats: { ...state.stats, [key]: value },
    })),
}));
