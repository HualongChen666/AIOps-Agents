/**
 * Batch 17 regression — database pages:
 *   FE-231 app/database/database-monitoring/page.tsx
 *        health check previously "Simulate[d] ... based on performance metrics";
 *        now it must call the real /api/v1/database-monitoring/health endpoint.
 *   FE-233 app/database/database-optimization/page.tsx
 *        suggestions were derived inside Promise.all from *stale* React state
 *        (always empty); now they must be derived from the freshly fetched data.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as {
  get: jest.Mock;
  put: jest.Mock;
  post: jest.Mock;
};

import DatabaseMonitoringPage from '@/app/database/database-monitoring/page';
import DatabaseOptimizationPage from '@/app/database/database-optimization/page';

describe('batch17 database pages use real data', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('FE-231 database-monitoring probes the real health endpoint', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url === '/api/v1/database-monitoring/health') {
        return Promise.resolve({
          data: {
            status: 'healthy',
            metrics: {
              query_time_ms: 12.5,
              connection_count: 20,
              cache_hit_ratio: 0.97,
              database_size_mb: 2048,
            },
            alerts: { active: 0, last_24h: 0 },
          },
        });
      }
      if (url.startsWith('/api/v1/database/performance')) {
        return Promise.resolve({ data: { cpu_usage: 5, memory_usage: 5, query_latency: 1, connection_count: 1, disk_io: 1 } });
      }
      if (url.startsWith('/api/v1/database/queries')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });

    render(<DatabaseMonitoringPage />);

    await waitFor(() =>
      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/database-monitoring/health'),
    );

    // checks are derived from the real health payload
    await waitFor(() => expect(screen.getByText('Cache Hit Ratio')).toBeInTheDocument());
    expect(screen.getByText(/Cache hit ratio is 97.0%/)).toBeInTheDocument();
    expect(screen.getByText('Active Alerts')).toBeInTheDocument();
  });

  it('FE-233 database-optimization derives suggestions from fetched data (no stale-state race)', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/database/performance')) {
        return Promise.resolve({
          data: { cpu_usage: 5, memory_usage: 5, query_latency: 5, connection_count: 3, disk_io: 1 },
        });
      }
      if (url === '/api/v1/database/indexes') {
        return Promise.resolve({ data: [] });
      }
      if (url.includes('slow_only=true')) {
        return Promise.resolve({
          data: [
            {
              query: 'SELECT 1',
              table_name: 'orders',
              execution_count: 5,
              avg_duration_ms: 120,
              last_executed: '2026-09-16T00:00:00Z',
              database: 'production',
            },
          ],
        });
      }
      if (url.includes('slow_only=false')) {
        return Promise.resolve({
          data: [
            {
              query: 'SELECT 1',
              table_name: 'orders',
              execution_count: 5,
              avg_duration_ms: 120,
              last_executed: '2026-09-16T00:00:00Z',
              database: 'production',
            },
          ],
        });
      }
      if (url.startsWith('/api/v1/database/optimization')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });

    render(<DatabaseOptimizationPage />);

    // The suggestion can only exist if it was derived from the fetched slow query.
    await waitFor(() => expect(screen.getByText('优化慢查询')).toBeInTheDocument());
    expect(screen.getByText(/发现 1 个慢查询/)).toBeInTheDocument();
  });
});
