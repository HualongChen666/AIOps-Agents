'use client'

import React, { useState, useEffect } from 'react';
import { DashboardCards } from '@/components/DashboardCards';
import { AlertStream } from '@/components/AlertStream';
import { SystemHealth } from '@/components/SystemHealth';
import { QuickActions } from '@/components/QuickActions';
import { MetricsChart } from '@/components/MetricsChart';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';

export default function OverviewPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<any>(null);

  // Real health probe: `fetch` resolves for 4xx/5xx too, so a missing `res.ok`
  // check would report success even when the backend is down.
  const probeBackend = async () => {
    const res = await fetch('/api/v1/health/ping');
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await probeBackend();
      setData(result);
      setError(null);
      success('Dashboard refreshed successfully');
    } catch (err) {
      showError('Failed to refresh dashboard');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    probeBackend()
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section>
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-[var(--dds-slate-90)]">
              AIOps 实时仪表盘
            </h1>
            {data?.status && (
              <span
                data-testid="backend-status"
                className={`text-xs px-2 py-1 rounded ${data.status === 'alive' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}
              >
                后端: {data.status}
              </span>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-[var(--dds-blue-60)] text-white rounded hover:bg-[var(--dds-blue-70)] disabled:opacity-50"
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="space-y-4">
          <QuickActions />
          <DashboardCards />
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MetricsChart />
        <SystemHealth />
      </section>

      <section>
        <AlertStream />
      </section>
    </div>
  );
}
