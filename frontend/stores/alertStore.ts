import { create } from 'zustand';

interface Alert {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'acknowledged' | 'resolved';
  timestamp: string;
  service: string;
}

interface AlertState {
  alerts: Alert[];
  selectedAlerts: Set<string>;
  filters: {
    severity: string;
    status: string;
    service: string;
  };
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  updateAlert: (id: string, updates: Partial<Alert>) => void;
  deleteAlert: (id: string) => void;
  toggleAlertSelection: (id: string) => void;
  clearSelection: () => void;
  setFilters: (filters: Partial<AlertState['filters']>) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  selectedAlerts: new Set(),
  filters: {
    severity: 'all',
    status: 'all',
    service: '',
  },
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
    })),
  updateAlert: (id, updates) =>
    set((state) => ({
      alerts: state.alerts.map((alert) =>
        alert.id === id ? { ...alert, ...updates } : alert
      ),
    })),
  deleteAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.filter((alert) => alert.id !== id),
    })),
  toggleAlertSelection: (id) =>
    set((state) => {
      const newSelection = new Set(state.selectedAlerts);
      if (newSelection.has(id)) {
        newSelection.delete(id);
      } else {
        newSelection.add(id);
      }
      return { selectedAlerts: newSelection };
    }),
  clearSelection: () => set({ selectedAlerts: new Set() }),
  setFilters: (filters) =>
    set((state) => ({
      filters: { ...state.filters, ...filters },
    })),
}));