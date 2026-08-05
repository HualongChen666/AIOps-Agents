'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface KPIMetric {
  name: string;
  value: number;
  target: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
}

interface KPIReport {
  id: string;
  name: string;
  period: string;
  createdAt: string;
}

interface DashboardMetricItem {
  key: string;
  value: number | string;
  unit: string;
  level?: string;
}

const targetByName: Record<string, number> = {
  告警数量: 50,
  自愈成功率: 85,
  MTTD: 30,
  MTTR: 30,
  MTBF: 720,
  告警响应时间: 10,
  自动修复成功率: 85,
  SLA达成率: 95,
  'RCA准确率': 85,
  决策准确率: 90,
  反馈准确率: 90,
  'CPU 使用率': 80,
  '内存使用率': 80,
  '磁盘使用率': 80,
  系统可用性: 99.9,
};

const unitByName: Record<string, string> = {
  告警数量: '个',
  自愈成功率: '%',
  MTTD: 'min',
  MTTR: 'min',
  MTBF: '小时',
  告警响应时间: 'min',
  自动修复成功率: '%',
  SLA达成率: '%',
  'RCA准确率': '%',
  决策准确率: '%',
  反馈准确率: '%',
  'CPU 使用率': '%',
  '内存使用率': '%',
  '磁盘使用率': '%',
  系统可用性: '%',
};

const parseMetricValue = (value: unknown): number => {
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const cleaned = value.replace(/%/g, '').trim();
    const parsed = parseFloat(cleaned);
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  return 0;
};

const SERIES_COLORS: Record<string, string> = {
  cpu: '#3b82f6',
  memory: '#ef4444',
  net_in: '#22c55e',
};

export default function KPIPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [kpiMetrics, setKpiMetrics] = useState<KPIMetric[]>([]);
  const [history, setHistory] = useState<Record<string, (number | string)[]>>({});
  const [reports, setReports] = useState<KPIReport[]>([]);

  useEffect(() => {
    let cancelled = false;

    const loadKPIs = async () => {
      try {
        const [summaryRes, snapshotRes, decisionRes, feedbackRes, historyRes] = await Promise.all([
          api.get('/api/v1/metrics/summary'),
          api.get('/api/v1/metrics/snapshot'),
          api.get('/api/v1/metrics/agent/decision-accuracy'),
          api.get('/api/v1/metrics/agent/feedback-accuracy'),
          api.get('/api/v1/metrics/history'),
        ]);

        if (cancelled) return;

        const nextMetrics: KPIMetric[] = [];
        const summary = summaryRes.data || {};

        // 总览摘要：优先使用顶层字段，兼容嵌套 alerts/repairs/systems
        const alertCount =
          summary.total_alerts ?? summary.alerts?.total ?? 0;
        const healRate =
          summary.heal_rate ?? summary.repairs?.heal_rate ?? 0;
        const mttd =
          summary.mttd_min ?? summary.alerts?.mttd_min ?? 0;
        const rcaAccuracy =
          summary.rca_accuracy ?? summary.alerts?.rca_accuracy ?? 0;

        if (alertCount !== undefined) {
          nextMetrics.push({
            name: '告警数量',
            value: Number(alertCount) || 0,
            target: targetByName['告警数量'],
            unit: unitByName['告警数量'],
            trend: 'stable',
          });
        }
        if (healRate !== undefined) {
          nextMetrics.push({
            name: '自愈成功率',
            value: parseMetricValue(healRate),
            target: targetByName['自愈成功率'],
            unit: unitByName['自愈成功率'],
            trend: 'stable',
          });
        }
        if (mttd !== undefined) {
          nextMetrics.push({
            name: 'MTTD',
            value: parseMetricValue(mttd),
            target: targetByName.MTTD,
            unit: unitByName.MTTD,
            trend: 'stable',
          });
        }
        if (rcaAccuracy !== undefined) {
          nextMetrics.push({
            name: 'RCA准确率',
            value: parseMetricValue(rcaAccuracy),
            target: targetByName['RCA准确率'],
            unit: unitByName['RCA准确率'],
            trend: 'stable',
          });
        }

        // 全量快照：CPU / 内存 / 磁盘
        const snapshot = snapshotRes.data || {};
        const cpu = snapshot.cpu?.usage_percent;
        const memory = snapshot.memory?.usage_percent;
        const disk = snapshot.disk?.usage_percent;

        if (typeof cpu === 'number') {
          nextMetrics.push({
            name: 'CPU 使用率',
            value: cpu,
            target: targetByName['CPU 使用率'],
            unit: unitByName['CPU 使用率'],
            trend: 'stable',
          });
        }
        if (typeof memory === 'number') {
          nextMetrics.push({
            name: '内存使用率',
            value: memory,
            target: targetByName['内存使用率'],
            unit: unitByName['内存使用率'],
            trend: 'stable',
          });
        }
        if (typeof disk === 'number') {
          nextMetrics.push({
            name: '磁盘使用率',
            value: disk,
            target: targetByName['磁盘使用率'],
            unit: unitByName['磁盘使用率'],
            trend: 'stable',
          });
        }

        // Agent 决策准确率
        const decision = decisionRes.data || {};
        const decisionMetrics = decision.metrics || decision;
        if (decisionMetrics?.accuracy !== undefined) {
          const accuracy = typeof decisionMetrics.accuracy === 'number' ? decisionMetrics.accuracy : 0;
          nextMetrics.push({
            name: '决策准确率',
            value: accuracy <= 1 ? Math.round(accuracy * 10000) / 100 : parseMetricValue(accuracy),
            target: targetByName['决策准确率'],
            unit: unitByName['决策准确率'],
            trend: 'stable',
          });
        }

        // Agent 反馈准确率
        const feedback = feedbackRes.data || {};
        if (feedback?.accuracy !== undefined) {
          nextMetrics.push({
            name: '反馈准确率',
            value: parseMetricValue(feedback.accuracy),
            target: targetByName['反馈准确率'],
            unit: unitByName['反馈准确率'],
            trend: 'stable',
          });
        }

        setKpiMetrics(nextMetrics);
        setHistory(historyRes.data || {});

        // 用当前快照时间生成一条动态 KPI 快照报告
        const createdAt = new Date().toISOString();
        setReports([
          {
            id: 'KPI-SNAP-001',
            name: `${selectedPeriod}KPI实时快照`,
            period: selectedPeriod,
            createdAt,
          },
        ]);
      } catch {
        // api interceptor 已展示错误提示
      }
    };

    loadKPIs();
    return () => {
      cancelled = true;
    };
  }, [selectedPeriod]);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      case 'stable':
        return '➡️';
      default:
        return '➡️';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      case 'stable':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  const getProgressColor = (value: number, target: number) => {
    const ratio = value / target;
    if (ratio >= 1) return 'bg-green-500';
    if (ratio >= 0.9) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const chartSeries = Object.entries(history).filter(
    ([key, values]) =>
      !key.startsWith('_') &&
      key !== 'timestamps' &&
      Array.isArray(values) &&
      values.length > 0
  );

  const width = 300;
  const height = 100;
  const allValues = chartSeries.flatMap(([, values]) =>
    (values as (number | string)[]).map((v) => parseMetricValue(v))
  );
  const maxValue = Math.max(1, ...allValues);

  const buildPoints = (values: (number | string)[]) => {
    const numbers = values.map((v) => parseMetricValue(v));
    if (numbers.length === 1) return `${0},${height - (numbers[0] / maxValue) * height}`;
    return numbers
      .map((v, i) => {
        const x = (i / (numbers.length - 1)) * width;
        const y = height - (v / maxValue) * height;
        return `${x},${y}`;
      })
      .join(' ');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">KPI监控</h1>
        <div className="flex gap-2">
          <Select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
          >
            <option value="day">日</option>
            <option value="week">周</option>
            <option value="month">月</option>
            <option value="quarter">季度</option>
          </Select>
          <Button>导出报告</Button>
        </div>
      </div>

      {/* KPI仪表盘 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpiMetrics.map((metric) => (
          <Card key={metric.name}>
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span>{metric.name}</span>
                <span className={getTrendColor(metric.trend)}>{getTrendIcon(metric.trend)}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">{metric.value}</span>
                  <span className="text-sm text-gray-500">{metric.unit}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">目标: {metric.target}{metric.unit}</span>
                  <span className={metric.value >= metric.target ? 'text-green-600' : 'text-red-600'}>
                    {metric.value >= metric.target ? '达标' : '未达标'}
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getProgressColor(metric.value, metric.target)}`}
                    style={{ width: `${Math.min(100, (metric.value / metric.target) * 100)}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 历史趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>KPI历史趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-gray-50 rounded-lg flex flex-col items-center justify-center p-4">
            {chartSeries.length === 0 ? (
              <p className="text-gray-500">KPI历史趋势图 (使用ECharts渲染)</p>
            ) : (
              <>
                <svg
                  viewBox={`0 0 ${width} ${height}`}
                  className="w-full h-full"
                  preserveAspectRatio="none"
                >
                  {chartSeries.map(([key, values]) => (
                    <polyline
                      key={key}
                      fill="none"
                      stroke={SERIES_COLORS[key] || '#9ca3af'}
                      strokeWidth={2}
                      points={buildPoints(values as (number | string)[])}
                    />
                  ))}
                </svg>
                <ul className="flex gap-4 mt-2 text-sm">
                  {chartSeries.map(([key]) => (
                    <li key={key} className="flex items-center">
                      <span
                        className="inline-block w-3 h-3 rounded-full mr-1"
                        style={{ backgroundColor: SERIES_COLORS[key] || '#9ca3af' }}
                      />
                      {key}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* KPI报告列表 */}
      <Card>
        <CardHeader>
          <CardTitle>KPI报告</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>报告名称</TableHead>
                <TableHead>周期</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.map((report) => (
                <TableRow key={report.id}>
                  <TableCell className="font-medium">{report.name}</TableCell>
                  <TableCell>{report.period}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(report.createdAt).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        查看
                      </Button>
                      <Button variant="outline" size="sm">
                        下载
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* KPI配置 */}
      <Card>
        <CardHeader>
          <CardTitle>KPI配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">报告周期</label>
              <Select>
                <option value="daily">每日</option>
                <option value="weekly">每周</option>
                <option value="monthly">每月</option>
                <option value="quarterly">每季度</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">自动生成</label>
              <Select>
                <option value="enabled">启用</option>
                <option value="disabled">禁用</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">邮件通知</label>
              <Select>
                <option value="enabled">启用</option>
                <option value="disabled">禁用</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">通知收件人</label>
              <Select>
                <option value="all">全部成员</option>
                <option value="admins">仅管理员</option>
                <option value="custom">自定义</option>
              </Select>
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <Button>保存配置</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
