import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as jest.Mocked<{
  get: jest.Mock;
  post: jest.Mock;
  put: jest.Mock;
  patch: jest.Mock;
  delete: jest.Mock;
}>;

// Dashboard children pull react-query/websockets; stub them so the test
// isolates the data-contract logic under test.
jest.mock('@/components/DashboardCards', () => ({ DashboardCards: () => null }));
jest.mock('@/components/AlertStream', () => ({ AlertStream: () => null }));
jest.mock('@/components/charts/HealTimeline', () => ({ HealTimeline: () => null }));
jest.mock('@/components/charts/ResourceTrendChart', () => ({
  ResourceTrendChart: ({ data }: { data: any[] }) => (
    <div data-testid="resource-trend-chart">{data.length} points</div>
  ),
}));
jest.mock('@/store/dashboard', () => ({
  useDashboardStore: () => ({ stats: {}, setStats: jest.fn() }),
}));

import DashboardPage from '@/app/dashboard/page';
import AlertStatisticsPage from '@/app/alerts/alert-statistics/page';
import AlertTrendsPage from '@/app/alerts/alert-trends/page';
import AlertsAdvancedPage from '@/app/alerts/alerts-advanced/page';

const renderPage = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedApi.get.mockResolvedValue({ data: {} });
  mockedApi.post.mockResolvedValue({ data: {} });
  mockedApi.put.mockResolvedValue({ data: {} });
  mockedApi.patch.mockResolvedValue({ data: {} });
  mockedApi.delete.mockResolvedValue({ data: {} });
});

describe('FE-215 app/dashboard — real history contract + real health endpoint', () => {
  it('builds resource points from the real cpu/memory/disk arrays', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/metrics/history')) {
        return Promise.resolve({
          data: {
            cpu: [10, 20],
            memory: [30, 40],
            net_in: [1, 2],
            disk: [50, 60],
            timestamps: ['10:00:00', '10:01:00'],
            _meta: { size: 2, maxlen: 60 },
          },
        });
      }
      if (url.startsWith('/api/v1/monitoring/detailed-health')) {
        return Promise.resolve({
          data: {
            overall_status: 'healthy',
            total_components: 2,
            healthy_components: 2,
            degraded_components: 0,
            unhealthy_components: 0,
            components: [
              { name: 'Database', status: 'healthy', response_time_ms: 3.2 },
              { name: 'Cache', status: 'healthy', response_time_ms: 1.1 },
            ],
            system_metrics: { cpu_usage: 12.5, memory_usage: 40, disk_usage: 55 },
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    renderPage(<DashboardPage />);

    // The chart receives 2 real points (it was always empty before).
    expect(await screen.findByText('2 points')).toBeInTheDocument();
    // The health card renders the real probed components.
    expect(await screen.findByText('Database')).toBeInTheDocument();
    expect(screen.getByText('Cache')).toBeInTheDocument();
    expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
  });

  it('never calls the non-existent /api/v1/health route', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/monitoring/detailed-health')) {
        return Promise.resolve({
          data: {
            overall_status: 'healthy',
            total_components: 0,
            healthy_components: 0,
            degraded_components: 0,
            unhealthy_components: 0,
            components: [],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    renderPage(<DashboardPage />);

    await screen.findByText('系统健康状态');
    const urls = mockedApi.get.mock.calls.map((c) => c[0] as string);
    expect(urls).toEqual(expect.arrayContaining(['/api/v1/monitoring/detailed-health']));
    expect(urls).not.toContain('/api/v1/health');
  });
});

describe('FE-188 app/alerts/alert-statistics — honest averages + no NaN', () => {
  const statBase = {
    total_alerts: 0,
    open_alerts: 0,
    acknowledged_alerts: 0,
    resolved_alerts: 0,
    critical_alerts: 0,
    high_alerts: 0,
    medium_alerts: 0,
    low_alerts: 0,
    avg_resolution_time: null as number | null,
    avg_acknowledgement_time: null as number | null,
    alerts_by_source: [],
    alerts_by_service: [],
    alerts_by_hour: [],
    alerts_by_day: [],
  };

  it('shows "—" for a null average and renders no NaN widths', async () => {
    mockedApi.get.mockResolvedValue({ data: { ...statBase } });

    const { container } = renderPage(<AlertStatisticsPage />);

    expect(await screen.findByText('—')).toBeInTheDocument();
    expect(container.innerHTML).not.toContain('NaN');
  });

  it('renders the real computed average (seconds → minutes)', async () => {
    mockedApi.get.mockResolvedValue({
      data: { ...statBase, total_alerts: 4, critical_alerts: 1, avg_resolution_time: 600 },
    });

    renderPage(<AlertStatisticsPage />);

    expect(await screen.findByText('10m')).toBeInTheDocument();
  });
});

describe('FE-190 app/alerts/alert-trends — renders the real backend prediction', () => {
  it('plots prediction points and hides the empty hint', async () => {
    mockedApi.get.mockResolvedValue({
      data: {
        daily_trends: [
          { date: '2026-09-10', total: 2, critical: 1, high: 1, medium: 0, low: 0 },
        ],
        weekly_trends: [],
        monthly_trends: [],
        prediction: [
          { date: '2026-09-17', total: 3, critical: 1, high: 1, medium: 1, low: 0 },
          { date: '2026-09-18', total: 4, critical: 2, high: 1, medium: 1, low: 0 },
        ],
      },
    });

    renderPage(<AlertTrendsPage />);

    expect(await screen.findByText('2026-09-17')).toBeInTheDocument();
    expect(screen.getByText('2026-09-18')).toBeInTheDocument();
    expect(screen.queryByText('暂无可用于预测的历史告警数据')).not.toBeInTheDocument();
  });

  it('shows the empty hint when there is no prediction', async () => {
    mockedApi.get.mockResolvedValue({
      data: {
        daily_trends: [],
        weekly_trends: [],
        monthly_trends: [],
        prediction: [],
      },
    });

    renderPage(<AlertTrendsPage />);

    expect(
      await screen.findByText('暂无可用于预测的历史告警数据')
    ).toBeInTheDocument();
  });
});

describe('FE-187 app/alerts/alerts-advanced — PUT toggle, blurred config, honest average', () => {
  const config = {
    id: 'c1',
    enabled: true,
    default_severity: 'medium',
    auto_resolve_timeout: 60,
    max_alerts_per_source: 10,
    enable_intelligent_analysis: true,
    enable_prediction: false,
    enable_correlation: false,
    retention_days: 30,
    notification_cooldown: 300,
    escalation_enabled: true,
    suppression_enabled: true,
  };

  const mockAlerts = () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url.includes('/alerts/dashboard')) {
        return Promise.resolve({
          data: {
            total_alerts: 1,
            open_alerts: 1,
            resolved_alerts: 0,
            critical_alerts: 0,
            high_alerts: 0,
            medium_alerts: 0,
            low_alerts: 0,
            avg_resolution_time: null,
            alerts_by_source: [],
            alerts_by_severity: [],
            trend_data: [],
          },
        });
      }
      if (url.includes('/alerts/configuration')) {
        return Promise.resolve({ data: config });
      }
      if (url.includes('/alerts/notification/channels')) {
        return Promise.resolve({ data: { channels: [] } });
      }
      if (url.includes('/alerts/escalation/rules')) {
        return Promise.resolve({
          data: {
            rules: [
              {
                id: 'r1',
                name: 'E1',
                description: 'd',
                enabled: true,
                max_escalation_level: 2,
                match_conditions: [],
                escalation_levels: [],
              },
            ],
          },
        });
      }
      if (url.includes('/alerts/suppression/rules')) {
        return Promise.resolve({ data: { rules: [] } });
      }
      if (url.includes('/alerts/aggregation/rules')) {
        return Promise.resolve({ data: { rules: [] } });
      }
      return Promise.resolve({ data: {} });
    });
  };

  it('shows "—" for a null average resolution time', async () => {
    mockAlerts();
    renderPage(<AlertsAdvancedPage />);
    expect(await screen.findByText('—')).toBeInTheDocument();
  });

  it('toggles a rule with PUT because the backend has no PATCH route', async () => {
    mockAlerts();
    renderPage(<AlertsAdvancedPage />);

    await userEvent.click(await screen.findByText('升级规则'));
    const row = (await screen.findByText('E1')).closest('tr') as HTMLElement;
    fireEvent.click(within(row).getAllByRole('button')[0]);

    await waitFor(() =>
      expect(mockedApi.put).toHaveBeenCalledWith('/api/v1/alerts/escalation/rules/r1', {
        enabled: false,
      })
    );
    expect(mockedApi.patch).not.toHaveBeenCalled();
  });

  it('commits the configuration on blur, not on each keystroke', async () => {
    mockAlerts();
    renderPage(<AlertsAdvancedPage />);

    await userEvent.click(await screen.findByText('配置'));
    const input = await screen.findByDisplayValue('60');

    fireEvent.change(input, { target: { value: '90' } });
    expect(mockedApi.put).not.toHaveBeenCalled();

    fireEvent.blur(input);
    await waitFor(() =>
      expect(mockedApi.put).toHaveBeenCalledWith(
        '/api/v1/alerts/configuration',
        expect.objectContaining({ auto_resolve_timeout: 90 })
      )
    );
    expect(mockedApi.put).toHaveBeenCalledTimes(1);
  });
});
