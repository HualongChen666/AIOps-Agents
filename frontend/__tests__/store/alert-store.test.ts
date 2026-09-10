import { renderHook, act } from '@testing-library/react';
import { useAlertStore } from '@/store/alerts';

/**
 * Real (non-tautological) tests for the alert store that shipped with the app.
 *
 * The previous version of this file mocked `@/stores/alertStore` and then
 * asserted the behaviour of its own mock, so it verified nothing. The duplicate
 * `stores/` implementation has been removed; this suite exercises the surviving
 * `store/alerts` store directly.
 */

const makeAlert = (overrides: Record<string, unknown> = {}) => ({
  id: 'a1',
  title: 'CPU high',
  severity: 'critical' as const,
  status: 'open' as const,
  timestamp: '2024-01-01T00:00:00Z',
  service: 'api',
  ...overrides,
});

describe('store/alerts', () => {
  beforeEach(() => {
    act(() => {
      useAlertStore.getState().clearAlerts();
    });
  });

  it('starts with no alerts', () => {
    expect(useAlertStore.getState().alerts).toEqual([]);
  });

  it('adds new alerts to the front of the list', () => {
    act(() => {
      useAlertStore.getState().addAlert(makeAlert({ id: 'a1' }));
      useAlertStore.getState().addAlert(makeAlert({ id: 'a2' }));
    });

    const ids = useAlertStore.getState().alerts.map((a) => a.id);
    expect(ids).toEqual(['a2', 'a1']);
  });

  it('updates only the targeted alert', () => {
    act(() => {
      useAlertStore.getState().addAlert(makeAlert({ id: 'a1' }));
      useAlertStore.getState().addAlert(makeAlert({ id: 'a2' }));
      useAlertStore.getState().updateAlert('a1', { status: 'resolved' });
    });

    const byId = Object.fromEntries(
      useAlertStore.getState().alerts.map((a) => [a.id, a.status])
    );
    expect(byId).toEqual({ a1: 'resolved', a2: 'open' });
  });

  it('ignores updates for unknown ids', () => {
    act(() => {
      useAlertStore.getState().addAlert(makeAlert({ id: 'a1' }));
      useAlertStore.getState().updateAlert('nope', { status: 'resolved' });
    });

    expect(useAlertStore.getState().alerts[0].status).toBe('open');
  });

  it('removes an alert by id', () => {
    act(() => {
      useAlertStore.getState().addAlert(makeAlert({ id: 'a1' }));
      useAlertStore.getState().addAlert(makeAlert({ id: 'a2' }));
      useAlertStore.getState().removeAlert('a1');
    });

    expect(useAlertStore.getState().alerts.map((a) => a.id)).toEqual(['a2']);
  });

  it('clears every alert', () => {
    act(() => {
      useAlertStore.getState().addAlert(makeAlert());
      useAlertStore.getState().clearAlerts();
    });

    expect(useAlertStore.getState().alerts).toEqual([]);
  });

  it('notifies subscribed components', () => {
    const { result } = renderHook(() => useAlertStore());

    act(() => {
      result.current.addAlert(makeAlert({ id: 'live' }));
    });

    expect(result.current.alerts).toHaveLength(1);
    expect(result.current.alerts[0].id).toBe('live');
  });
});
