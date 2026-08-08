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

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch('/api/v1/health/ping');
      success('Dashboard refreshed successfully');
    } catch (err) {
      showError('Failed to refresh dashboard');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetch('/api/v1/health/ping')
      .then((res) => res.json())
      .then((data) => {
        setData(data);
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
          <h1 className="text-2xl font-bold text-[var(--dds-slate-90)]">
            AIOps 实时仪表盘
          </h1>
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
