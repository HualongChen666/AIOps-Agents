'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MetricCard {
  key: string;
  label: string;
  value: string;
  unit: string;
  level: 'normal' | 'warning' | 'critical';
  history: number[];
}

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<MetricCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      try {
        const [snapshotRes, historyRes] = await Promise.all([
          api.get('/api/v1/metrics/snapshot').catch(() => null),
          api.get('/api/v1/metrics/history').catch(() => null),
        ]);

        if (cancelled) return;

        const snapshot = snapshotRes?.data || null;
        const history = historyRes?.data || null;

        if (!snapshot || !history) {
          setError('无法获取性能数据，请稍后重试');
          setMetrics([]);
          setLoading(false);
          return;
        }

        const getLevel = (value: number | null): MetricCard['level'] => {
          if (value === null) return 'normal';
          if (value >= 90) return 'critical';
          if (value >= 70) return 'warning';
          return 'normal';
        };

        const getValue = (value: number | null): string => {
          if (value === null || Number.isNaN(value)) return '--';
          return value.toFixed(1);
        };

        const getHistory = (key: string): number[] => {
          const raw = history[key];
          if (!Array.isArray(raw)) return [];
          return raw.slice(-20).map((v) => Number(v) || 0);
        };

        const cpu = typeof snapshot.cpu?.usage_percent === 'number' ? snapshot.cpu.usage_percent : null;
        const memory = typeof snapshot.memory?.usage_percent === 'number' ? snapshot.memory.usage_percent : null;
        const disk = typeof snapshot.disk?.usage_percent === 'number' ? snapshot.disk.usage_percent : null;

        setMetrics([
          {
            key: 'cpu',
            label: 'CPU 使用率',
            value: getValue(cpu),
            unit: '%',
            level: getLevel(cpu),
            history: getHistory('cpu'),
          },
          {
            key: 'memory',
            label: '内存使用率',
            value: getValue(memory),
            unit: '%',
            level: getLevel(memory),
            history: getHistory('memory'),
          },
          {
            key: 'disk',
            label: '磁盘使用率',
            value: getValue(disk),
            unit: '%',
            level: getLevel(disk),
            history: [],
          },
        ]);
      } catch (err) {
        if (!cancelled) {
          setError('性能数据加载失败');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadData();
    return () => { cancelled = true; };
  }, []);

  const getLevelText = (level: string) => {
    switch (level) {
      case 'critical': return '严重';
      case 'warning': return '警告';
      case 'normal': return '正常';
      default: return level;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'normal': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const renderTrend = (history: number[]) => {
    if (history.length === 0) {
      return <p className="text-xs text-gray-400 mt-2">暂无历史趋势数据</p>;
    }
    const max = Math.max(1, ...history);
    return (
      <div className="flex items-end h-16 gap-1 mt-3">
        {history.map((value, index) => (
          <div
            key={index}
            className="flex-1 bg-blue-400 rounded-sm opacity-80"
            style={{ height: `${Math.round((value / max) * 100)}%` }}
            title={`${value.toFixed(1)}`}
          />
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-500">
        性能数据加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-red-600">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">性能监控</h1>
      </div>

      {metrics.length === 0 ? (
        <div className="text-sm text-gray-500">暂无可用性能指标</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {metrics.map((m) => (
            <Card key={m.key}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">{m.label}</CardTitle>
                  <Badge className={getLevelColor(m.level)}>
                    {getLevelText(m.level)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className={`text-2xl font-bold ${m.level === 'critical' ? 'text-red-600' : m.level === 'warning' ? 'text-yellow-600' : 'text-green-600'}`}>
                  {m.value}
                  <span className="text-sm font-normal text-gray-500 ml-1">{m.unit}</span>
                </p>
                <p className="text-xs text-gray-500 mt-1">实时快照 / 历史趋势</p>
                {renderTrend(m.history)}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
