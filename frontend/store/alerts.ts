import { create } from 'zustand';

interface Alert {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'acknowledged' | 'resolved';
  timestamp: string;
  service: string;
  details?: string;
}

interface AlertStore {
  alerts: Alert[];
  addAlert: (alert: Alert) => void;
  updateAlert: (id: string, updates: Partial<Alert>) => void;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts] })),
  updateAlert: (id, updates) =>
    set((state) => ({
      alerts: state.alerts.map((a) => (a.id === id ? { ...a, ...updates } : a)),
    })),
  removeAlert: (id) =>
    set((state) => ({ alerts: state.alerts.filter((a) => a.id !== id) })),
  clearAlerts: () => set({ alerts: [] }),
}));
