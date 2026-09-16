import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as jest.Mocked<{
  get: jest.Mock;
  post: jest.Mock;
  put: jest.Mock;
  patch: jest.Mock;
  delete: jest.Mock;
}>;

import MonitoringConfigPage from '@/app/monitoring/monitoring-config/page';

const renderPage = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

const mockConfigs = () => {
  mockedApi.get.mockImplementation((url: string) => {
    if (url === '/api/v1/monitoring/config') {
      return Promise.resolve({
        data: {
          enabled: true,
          data_retention_days: 45,
          sampling_rate: 0.5,
          enable_realtime: true,
          enable_historical: true,
          dashboard_refresh_interval: 25,
        },
      });
    }
    if (url === '/api/v1/monitoring/metrics-config') {
      return Promise.resolve({
        data: {
          cpu_enabled: true,
          memory_enabled: true,
          disk_enabled: true,
          network_enabled: true,
          process_enabled: true,
          collection_interval: 60,
          storage_backend: 'victoriametrics',
        },
      });
    }
    if (url === '/api/v1/monitoring/logging-config') {
      return Promise.resolve({
        data: {
          level: 'INFO',
          format: 'json',
          enable_file_logging: true,
          enable_console_logging: true,
          log_retention_days: 7,
          max_file_size_mb: 100,
          storage_backend: 'loki',
        },
      });
    }
    if (url === '/api/v1/monitoring/alert-thresholds') {
      return Promise.resolve({
        data: { thresholds: [], notification_channels: [], cooldown_seconds: 300 },
      });
    }
    if (url === '/api/v1/monitoring/status') {
      return Promise.resolve({ data: {} });
    }
    return Promise.resolve({ data: {} });
  });
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedApi.post.mockResolvedValue({ data: {} });
  mockedApi.put.mockResolvedValue({ data: {} });
  mockedApi.patch.mockResolvedValue({ data: {} });
  mockedApi.delete.mockResolvedValue({ data: {} });
});

describe('FE-259 app/monitoring/monitoring-config — draft + commit, not per keystroke', () => {
  it('does not PUT while typing a numeric field and commits once on blur', async () => {
    mockConfigs();
    renderPage(<MonitoringConfigPage />);

    const input = await screen.findByDisplayValue('45');
    fireEvent.change(input, { target: { value: '50' } });

    // Typing alone must not hit the backend.
    expect(mockedApi.put).not.toHaveBeenCalled();

    fireEvent.blur(input);

    await waitFor(() =>
      expect(mockedApi.put).toHaveBeenCalledWith(
        '/api/v1/monitoring/config',
        expect.objectContaining({ data_retention_days: 50 })
      )
    );
    expect(mockedApi.put).toHaveBeenCalledTimes(1);
  });

  it('commits a discrete toggle immediately with one PUT', async () => {
    mockConfigs();
    renderPage(<MonitoringConfigPage />);

    // The first switch in the general tab is "启用监控".
    const switchEl = (await screen.findAllByRole('switch'))[0];
    fireEvent.click(switchEl);

    await waitFor(() =>
      expect(mockedApi.put).toHaveBeenCalledWith(
        '/api/v1/monitoring/config',
        expect.objectContaining({ enabled: false })
      )
    );
    expect(mockedApi.put).toHaveBeenCalledTimes(1);
  });

  it('keeps the typed value visible (no query-driven overwrite jitter)', async () => {
    mockConfigs();
    renderPage(<MonitoringConfigPage />);

    const input = await screen.findByDisplayValue('45');
    fireEvent.change(input, { target: { value: '77' } });

    expect((input as HTMLInputElement).value).toBe('77');
  });
});
