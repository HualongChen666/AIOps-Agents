import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// The monitoring pages talk to the backend through the shared axios client.
jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as jest.Mocked<{
  get: jest.Mock;
  post: jest.Mock;
}>;

import MetricsHistoryPage from '@/app/monitoring/metrics-history/page';
import ProcessMonitoringPage from '@/app/monitoring/process-monitoring/page';
import PrometheusMetricsPage from '@/app/monitoring/prometheus-metrics/page';
import LogSearchPage from '@/app/monitoring/log-search/page';
import ObservabilityQueryPage from '@/app/monitoring/observability-query/page';
import LinuxMonitoringPage from '@/app/monitoring/linux-monitoring/page';
import WindowsMonitoringPage from '@/app/monitoring/windows-monitoring/page';
import FastAPITelemetryPage from '@/app/monitoring/fastapi-telemetry/page';
import TracingVisualizationPage from '@/app/monitoring/tracing-visualization/page';

const renderPage = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

beforeEach(() => {
  mockedApi.get.mockReset();
  mockedApi.post.mockReset();
  mockedApi.get.mockResolvedValue({ data: {} });
  mockedApi.post.mockResolvedValue({ data: {} });
});

describe('medium-ledger batch15 — monitoring pages read the real backend contract', () => {
  describe('FE-257 metrics-history', () => {
    it('requests `metric` and renders the nested data series', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          metric: 'cpu',
          time_range: '24h',
          data_points: 3,
          data: { cpu: [10, 20, 30], timestamps: ['00:00:00', '00:01:00', '00:02:00'] },
        },
      });

      renderPage(<MetricsHistoryPage />);

      await waitFor(() =>
        expect(mockedApi.get).toHaveBeenCalledWith(
          '/api/v1/monitoring/metrics-history',
          expect.objectContaining({ params: { time_range: '24h', metric: 'cpu' } })
        )
      );

      // average of [10,20,30] from the nested series (also echoed per-row)
      expect((await screen.findAllByText('20.00')).length).toBeGreaterThan(0);
      expect(screen.queryByText('暂无数据')).not.toBeInTheDocument();
      expect(screen.getByText('00:02:00')).toBeInTheDocument();
    });
  });

  describe('FE-262 process-monitoring', () => {
    it('uses the real `total_processes` field and `username` column', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          total_processes: 42,
          processes: [{ pid: 7, name: 'nginx', status: 'sleeping', username: 'www-data' }],
        },
      });

      renderPage(<ProcessMonitoringPage />);

      expect(await screen.findByText('42')).toBeInTheDocument();
      expect(screen.getByText('www-data')).toBeInTheDocument();
    });
  });

  describe('FE-263 prometheus-metrics', () => {
    it('maps the real `metric`/`value` series shape (not name/type/labels)', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          prometheus_url: 'http://prom:9090',
          query: 'up',
          metrics: [{ metric: { __name__: 'up', job: 'api' }, value: [1700000000, '1'] }],
        },
      });

      renderPage(<PrometheusMetricsPage />);

      expect(await screen.findByText('http://prom:9090')).toBeInTheDocument();
      // metric name falls back to the __name__ label (also shown as the query)
      expect((await screen.findAllByText('up')).length).toBeGreaterThan(0);
      expect(screen.getByText('job=api')).toBeInTheDocument();
      expect(screen.getByText('1.0000')).toBeInTheDocument();
    });
  });

  describe('FE-252 log-search', () => {
    it('queries with `keyword` and renders `total`', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          total: 1,
          keyword: 'error',
          logs: [{ TimeGenerated: '2024-01-01 00:00:00', Source: 'syslog', Message: 'boom' }],
        },
      });

      renderPage(<LogSearchPage />);

      fireEvent.change(screen.getByPlaceholderText('输入搜索关键词...'), {
        target: { value: 'error' },
      });
      fireEvent.click(screen.getByText('搜索'));

      await waitFor(() =>
        expect(mockedApi.get).toHaveBeenCalledWith(
          '/api/v1/monitoring/log-search',
          expect.objectContaining({ params: expect.objectContaining({ keyword: 'error' }) })
        )
      );
      expect(await screen.findByText('boom')).toBeInTheDocument();
      expect(screen.getByText('条日志')).toBeInTheDocument();
    });
  });

  describe('FE-260 observability-query', () => {
    it('renders the metric series carried under `data`', async () => {
      mockedApi.get.mockResolvedValue({
        data: { query_type: 'metrics', query: 'cpu', time_range: '1h', data: { cpu: [1, 2, 3] } },
      });

      renderPage(<ObservabilityQueryPage />);

      fireEvent.change(screen.getByPlaceholderText('输入查询条件...'), {
        target: { value: 'cpu' },
      });
      fireEvent.click(screen.getByText('查询'));

      expect(await screen.findByText('cpu')).toBeInTheDocument();
      expect(screen.getByText('3.00')).toBeInTheDocument();
    });
  });

  describe('FE-248 linux-monitoring', () => {
    it('reads the nested host/OS/cpu detail instead of flat keys', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          hostname: 'srv-a',
          os_version: 'Alibaba Cloud Linux',
          kernel_version: '5.10.0',
          uptime: 90061,
          cpu: { usage_percent: 12.5, cores: 4, load_avg: [0.1, 0.2, 0.3] },
          memory: { usage_percent: 40, total_gb: 16, used_gb: 6, available_gb: 10 },
          disk: { usage_percent: 55, total_gb: 100, used_gb: 55, free_gb: 45 },
          network: { interfaces: [{ name: 'eth0', ip: '10.0.0.2', rx_bytes: 1048576, tx_bytes: 2097152 }] },
        },
      });

      renderPage(<LinuxMonitoringPage />);

      expect(await screen.findByText('srv-a')).toBeInTheDocument();
      expect(screen.getByText('Alibaba Cloud Linux')).toBeInTheDocument();
      expect(screen.getByText('12.50%')).toBeInTheDocument();
      expect(screen.getByText('eth0')).toBeInTheDocument();
      expect(screen.getByText('10.0.0.2')).toBeInTheDocument();
    });
  });

  describe('FE-269 windows-monitoring', () => {
    it('renders real services and disk partitions from the nested payload', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          hostname: 'win-a',
          os_version: 'Windows Server 2022',
          kernel_version: '10.0.20348',
          uptime: 3600,
          cpu: { usage_percent: 20, cores: 8, logical_processors: 16 },
          memory: { usage_percent: 50, total_gb: 32, available_gb: 16 },
          processes: 128,
          disk_partitions: [
            { drive: 'C:\\', label: '\\\\?\\Volume1', usage_percent: 60, total_gb: 200, free_gb: 80 },
          ],
          services: [
            { name: 'wuauserv', display_name: 'Windows Update', status: 'running', start_type: 'manual' },
          ],
        },
      });

      renderPage(<WindowsMonitoringPage />);

      expect(await screen.findByText('win-a')).toBeInTheDocument();
      expect(screen.getByText('wuauserv')).toBeInTheDocument();
      expect(screen.getByText('Windows Update')).toBeInTheDocument();
      expect(screen.getByText('C:\\')).toBeInTheDocument();
      expect(screen.getByText('128')).toBeInTheDocument();
    });
  });

  describe('FE-244 fastapi-telemetry', () => {
    it('renders the real endpoints[] aggregate', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          fastapi_version: '0.115.0',
          total_requests: 250,
          total_errors: 5,
          avg_response_time_ms: 12.34,
          endpoints: [
            { path: '/api/v1/health', method: 'GET', request_count: 200, avg_latency_ms: 8.5, error_rate: 0.01 },
          ],
        },
      });

      renderPage(<FastAPITelemetryPage />);

      expect(await screen.findByText('0.115.0')).toBeInTheDocument();
      expect(screen.getByText('/api/v1/health')).toBeInTheDocument();
      expect(screen.getByText('12.34 ms')).toBeInTheDocument();
      expect(screen.getByText('1.00%')).toBeInTheDocument();
    });
  });

  describe('FE-267 tracing-visualization', () => {
    it('builds the trace tree from the real nodes/edges graph', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          trace_id: 't-1',
          total_spans: 3,
          total_duration_ms: 125.5,
          services: ['gateway', 'orders'],
          nodes: [
            { id: 'gateway', label: 'gateway' },
            { id: 'orders', label: 'orders' },
          ],
          edges: [{ source: 'gateway', target: 'orders', label: 'GET /orders', latency_ms: 42.1 }],
        },
      });

      renderPage(<TracingVisualizationPage />);

      fireEvent.change(screen.getByPlaceholderText('输入Trace ID...'), {
        target: { value: 't-1' },
      });
      fireEvent.click(screen.getByText('可视化'));

      expect((await screen.findAllByText('gateway')).length).toBeGreaterThan(0);
      expect(screen.getAllByText('orders').length).toBeGreaterThan(0);
      expect(screen.getByText('GET /orders')).toBeInTheDocument();
      expect(screen.getByText('125.50 ms')).toBeInTheDocument();
      expect(screen.queryByText('无追踪数据')).not.toBeInTheDocument();
    });
  });
});
