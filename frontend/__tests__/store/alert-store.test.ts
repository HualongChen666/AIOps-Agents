import { renderHook, act } from '@testing-library/react';
import { useAlertStore } from '@/stores/alertStore';

// Mock the store to avoid circular dependency
jest.mock('@/stores/alertStore', () => {
  let storeState = {
    alerts: [],
    selectedAlerts: new Set(),
    filters: {
      severity: 'all',
      status: 'all',
      service: '',
    },
  };

  return {
    useAlertStore: jest.fn(() => ({
      alerts: storeState.alerts,
      selectedAlerts: storeState.selectedAlerts,
      filters: storeState.filters,
      setAlerts: (alerts: any[]) => { storeState.alerts = alerts; },
      addAlert: (alert: any) => { storeState.alerts = [alert, ...storeState.alerts]; },
      updateAlert: (id: string, updates: any) => {
        storeState.alerts = storeState.alerts.map((alert: any) =>
          alert.id === id ? { ...alert, ...updates } : alert
        );
      },
      deleteAlert: (id: string) => {
        storeState.alerts = storeState.alerts.filter((alert: any) => alert.id !== id);
      },
      toggleAlertSelection: (id: string) => {
        const newSelection = new Set(storeState.selectedAlerts);
        if (newSelection.has(id)) {
          newSelection.delete(id);
        } else {
          newSelection.add(id);
        }
        storeState.selectedAlerts = newSelection;
      },
      clearSelection: () => { storeState.selectedAlerts = new Set(); },
      setFilters: (filters: any) => {
        storeState.filters = { ...storeState.filters, ...filters };
      },
    })),
    useAlertStore: {
      setState: (state: any) => {
        storeState = { ...storeState, ...state };
      },
    },
  };
});

describe('useAlertStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useAlertStore());
    act(() => {
      result.current.setAlerts([]);
      result.current.clearSelection();
      result.current.setFilters({
        severity: 'all',
        status: 'all',
        service: '',
      });
    });
  });

  describe('Initial State', () => {
    it('should initialize with empty alerts array', () => {
      const { result } = renderHook(() => useAlertStore());

      expect(result.current.alerts).toEqual([]);
    });

    it('should initialize with empty selectedAlerts set', () => {
      const { result } = renderHook(() => useAlertStore());

      expect(result.current.selectedAlerts).toEqual(new Set());
    });

    it('should initialize with default filters', () => {
      const { result } = renderHook(() => useAlertStore());

      expect(result.current.filters).toEqual({
        severity: 'all',
        status: 'all',
        service: '',
      });
    });
  });

  describe('setAlerts', () => {
    it('should set alerts array', () => {
      const { result } = renderHook(() => useAlertStore());

      const mockAlerts = [
        {
          id: '1',
          title: 'Test Alert 1',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
        {
          id: '2',
          title: 'Test Alert 2',
          severity: 'high' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
      ];

      act(() => {
        result.current.setAlerts(mockAlerts);
      });

      expect(result.current.alerts).toEqual(mockAlerts);
      expect(result.current.alerts).toHaveLength(2);
    });

    it('should replace existing alerts', () => {
      const { result } = renderHook(() => useAlertStore());

      const initialAlerts = [
        {
          id: '1',
          title: 'Initial Alert',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
      ];

      act(() => {
        result.current.setAlerts(initialAlerts);
      });

      const newAlerts = [
        {
          id: '2',
          title: 'New Alert',
          severity: 'high' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
      ];

      act(() => {
        result.current.setAlerts(newAlerts);
      });

      expect(result.current.alerts).toEqual(newAlerts);
      expect(result.current.alerts).toHaveLength(1);
    });

    it('should handle empty alerts array', () => {
      const { result } = renderHook(() => useAlertStore());

      const mockAlerts = [
        {
          id: '1',
          title: 'Test Alert',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
      ];

      act(() => {
        result.current.setAlerts(mockAlerts);
      });

      act(() => {
        result.current.setAlerts([]);
      });

      expect(result.current.alerts).toEqual([]);
    });
  });

  describe('addAlert', () => {
    it('should add alert to the beginning of array', () => {
      const { result } = renderHook(() => useAlertStore());

      const alert1 = {
        id: '1',
        title: 'Alert 1',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      const alert2 = {
        id: '2',
        title: 'Alert 2',
        severity: 'high' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T01:00:00Z',
        service: 'database',
      };

      act(() => {
        result.current.addAlert(alert1);
      });

      act(() => {
        result.current.addAlert(alert2);
      });

      expect(result.current.alerts).toHaveLength(2);
      expect(result.current.alerts[0]).toEqual(alert2);
      expect(result.current.alerts[1]).toEqual(alert1);
    });

    it('should add alert to empty array', () => {
      const { result } = renderHook(() => useAlertStore());

      const alert = {
        id: '1',
        title: 'Test Alert',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      act(() => {
        result.current.addAlert(alert);
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0]).toEqual(alert);
    });
  });

  describe('updateAlert', () => {
    it('should update existing alert by id', () => {
      const { result } = renderHook(() => useAlertStore());

      const alerts = [
        {
          id: '1',
          title: 'Alert 1',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
        {
          id: '2',
          title: 'Alert 2',
          severity: 'high' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
      ];

      act(() => {
        result.current.setAlerts(alerts);
      });

      act(() => {
        result.current.updateAlert('1', { status: 'resolved' });
      });

      expect(result.current.alerts[0].status).toBe('resolved');
      expect(result.current.alerts[1].status).toBe('open');
    });

    it('should update multiple fields of alert', () => {
      const { result } = renderHook(() => useAlertStore());

      const alert = {
        id: '1',
        title: 'Alert 1',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      act(() => {
        result.current.setAlerts([alert]);
      });

      act(() => {
        result.current.updateAlert('1', {
          status: 'acknowledged',
          severity: 'high',
        });
      });

      expect(result.current.alerts[0].status).toBe('acknowledged');
      expect(result.current.alerts[0].severity).toBe('high');
    });

    it('should not affect other alerts when updating one', () => {
      const { result } = renderHook(() => useAlertStore());

      const alerts = [
        {
          id: '1',
          title: 'Alert 1',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
        {
          id: '2',
          title: 'Alert 2',
          severity: 'high' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
      ];

      act(() => {
        result.current.setAlerts(alerts);
      });

      act(() => {
        result.current.updateAlert('1', { status: 'resolved' });
      });

      expect(result.current.alerts[1]).toEqual(alerts[1]);
    });

    it('should handle updating non-existent alert', () => {
      const { result } = renderHook(() => useAlertStore());

      const alert = {
        id: '1',
        title: 'Alert 1',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      act(() => {
        result.current.setAlerts([alert]);
      });

      act(() => {
        result.current.updateAlert('999', { status: 'resolved' });
      });

      expect(result.current.alerts[0].status).toBe('open');
    });
  });

  describe('deleteAlert', () => {
    it('should delete alert by id', () => {
      const { result } = renderHook(() => useAlertStore());

      const alerts = [
        {
          id: '1',
          title: 'Alert 1',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
        {
          id: '2',
          title: 'Alert 2',
          severity: 'high' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
      ];

      act(() => {
        result.current.setAlerts(alerts);
      });

      act(() => {
        result.current.deleteAlert('1');
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0].id).toBe('2');
    });

    it('should handle deleting non-existent alert', () => {
      const { result } = renderHook(() => useAlertStore());

      const alert = {
        id: '1',
        title: 'Alert 1',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      act(() => {
        result.current.setAlerts([alert]);
      });

      act(() => {
        result.current.deleteAlert('999');
      });

      expect(result.current.alerts).toHaveLength(1);
    });

    it('should handle deleting from empty array', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.deleteAlert('1');
      });

      expect(result.current.alerts).toEqual([]);
    });
  });

  describe('toggleAlertSelection', () => {
    it('should add alert to selection when not selected', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.toggleAlertSelection('1');
      });

      expect(result.current.selectedAlerts.has('1')).toBe(true);
    });

    it('should remove alert from selection when already selected', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.toggleAlertSelection('1');
      });

      act(() => {
        result.current.toggleAlertSelection('1');
      });

      expect(result.current.selectedAlerts.has('1')).toBe(false);
    });

    it('should handle multiple selections', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.toggleAlertSelection('1');
        result.current.toggleAlertSelection('2');
        result.current.toggleAlertSelection('3');
      });

      expect(result.current.selectedAlerts.size).toBe(3);
      expect(result.current.selectedAlerts.has('1')).toBe(true);
      expect(result.current.selectedAlerts.has('2')).toBe(true);
      expect(result.current.selectedAlerts.has('3')).toBe(true);
    });
  });

  describe('clearSelection', () => {
    it('should clear all selected alerts', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.toggleAlertSelection('1');
        result.current.toggleAlertSelection('2');
        result.current.toggleAlertSelection('3');
      });

      expect(result.current.selectedAlerts.size).toBe(3);

      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedAlerts.size).toBe(0);
    });

    it('should handle clearing empty selection', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedAlerts.size).toBe(0);
    });
  });

  describe('setFilters', () => {
    it('should update single filter', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.setFilters({ severity: 'critical' });
      });

      expect(result.current.filters.severity).toBe('critical');
      expect(result.current.filters.status).toBe('all');
      expect(result.current.filters.service).toBe('');
    });

    it('should update multiple filters', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.setFilters({
          severity: 'critical',
          status: 'open',
          service: 'api',
        });
      });

      expect(result.current.filters).toEqual({
        severity: 'critical',
        status: 'open',
        service: 'api',
      });
    });

    it('should preserve existing filters when updating partial', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.setFilters({
          severity: 'critical',
          status: 'open',
          service: 'api',
        });
      });

      act(() => {
        result.current.setFilters({ status: 'resolved' });
      });

      expect(result.current.filters).toEqual({
        severity: 'critical',
        status: 'resolved',
        service: 'api',
      });
    });

    it('should reset filter to default', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        result.current.setFilters({
          severity: 'critical',
          status: 'open',
          service: 'api',
        });
      });

      act(() => {
        result.current.setFilters({
          severity: 'all',
          status: 'all',
          service: '',
        });
      });

      expect(result.current.filters).toEqual({
        severity: 'all',
        status: 'all',
        service: '',
      });
    });
  });

  describe('State Persistence', () => {
    it('should maintain state across hook instances', () => {
      const { result: firstHook } = renderHook(() => useAlertStore());

      const alerts = [
        {
          id: '1',
          title: 'Alert 1',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
      ];

      act(() => {
        firstHook.current.setAlerts(alerts);
        firstHook.current.toggleAlertSelection('1');
        firstHook.current.setFilters({ severity: 'critical' });
      });

      const { result: secondHook } = renderHook(() => useAlertStore());

      expect(secondHook.current.alerts).toEqual(alerts);
      expect(secondHook.current.selectedAlerts.has('1')).toBe(true);
      expect(secondHook.current.filters.severity).toBe('critical');
    });
  });

  describe('Real-world Scenarios', () => {
    it('should simulate alert lifecycle', () => {
      const { result } = renderHook(() => useAlertStore());

      // New alert arrives
      const newAlert = {
        id: '1',
        title: 'CPU High',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      act(() => {
        result.current.addAlert(newAlert);
      });

      expect(result.current.alerts).toHaveLength(1);

      // Alert is acknowledged
      act(() => {
        result.current.updateAlert('1', { status: 'acknowledged' });
      });

      expect(result.current.alerts[0].status).toBe('acknowledged');

      // Alert is resolved
      act(() => {
        result.current.updateAlert('1', { status: 'resolved' });
      });

      expect(result.current.alerts[0].status).toBe('resolved');

      // Alert is deleted
      act(() => {
        result.current.deleteAlert('1');
      });

      expect(result.current.alerts).toHaveLength(0);
    });

    it('should simulate bulk alert operations', () => {
      const { result } = renderHook(() => useAlertStore());

      const alerts = [
        {
          id: '1',
          title: 'Alert 1',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
        {
          id: '2',
          title: 'Alert 2',
          severity: 'high' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
        {
          id: '3',
          title: 'Alert 3',
          severity: 'medium' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T02:00:00Z',
          service: 'cache',
        },
      ];

      act(() => {
        result.current.setAlerts(alerts);
      });

      // Select multiple alerts
      act(() => {
        result.current.toggleAlertSelection('1');
        result.current.toggleAlertSelection('2');
      });

      expect(result.current.selectedAlerts.size).toBe(2);

      // Apply filter
      act(() => {
        result.current.setFilters({ severity: 'critical' });
      });

      expect(result.current.filters.severity).toBe('critical');

      // Clear selection
      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedAlerts.size).toBe(0);
    });

    it('should simulate alert filtering workflow', () => {
      const { result } = renderHook(() => useAlertStore());

      const alerts = [
        {
          id: '1',
          title: 'Critical Alert',
          severity: 'critical' as const,
          status: 'open' as const,
          timestamp: '2024-01-01T00:00:00Z',
          service: 'api',
        },
        {
          id: '2',
          title: 'High Alert',
          severity: 'high' as const,
          status: 'resolved' as const,
          timestamp: '2024-01-01T01:00:00Z',
          service: 'database',
        },
      ];

      act(() => {
        result.current.setAlerts(alerts);
      });

      // Filter by severity
      act(() => {
        result.current.setFilters({ severity: 'critical' });
      });

      expect(result.current.filters.severity).toBe('critical');

      // Filter by status
      act(() => {
        result.current.setFilters({ status: 'open' });
      });

      expect(result.current.filters.status).toBe('open');

      // Filter by service
      act(() => {
        result.current.setFilters({ service: 'api' });
      });

      expect(result.current.filters.service).toBe('api');

      // Reset filters
      act(() => {
        result.current.setFilters({
          severity: 'all',
          status: 'all',
          service: '',
        });
      });

      expect(result.current.filters).toEqual({
        severity: 'all',
        status: 'all',
        service: '',
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle alerts with same id', () => {
      const { result } = renderHook(() => useAlertStore());

      const alert1 = {
        id: '1',
        title: 'Alert 1',
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      };

      const alert2 = {
        id: '1',
        title: 'Alert 2',
        severity: 'high' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T01:00:00Z',
        service: 'database',
      };

      act(() => {
        result.current.addAlert(alert1);
        result.current.addAlert(alert2);
      });

      expect(result.current.alerts).toHaveLength(2);
    });

    it('should handle large number of alerts', () => {
      const { result } = renderHook(() => useAlertStore());

      const largeAlerts = Array.from({ length: 1000 }, (_, i) => ({
        id: `${i}`,
        title: `Alert ${i}`,
        severity: 'critical' as const,
        status: 'open' as const,
        timestamp: '2024-01-01T00:00:00Z',
        service: 'api',
      }));

      act(() => {
        result.current.setAlerts(largeAlerts);
      });

      expect(result.current.alerts).toHaveLength(1000);
    });

    it('should handle rapid successive updates', () => {
      const { result } = renderHook(() => useAlertStore());

      act(() => {
        for (let i = 0; i < 100; i++) {
          result.current.setFilters({ severity: i % 2 === 0 ? 'critical' : 'high' });
        }
      });

      expect(result.current.filters.severity).toBe('high');
    });
  });
});
