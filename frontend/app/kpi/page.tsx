'use client'

import { useEffect, useMemo, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface KPIMetric {
  id: string;
  name: string;
  value: number;
  target: number;
  unit: string;
  endpoint?: string;
  field_path?: string;
}

interface KPIConfig {
  id: string;
  name: string;
  endpoint: string;
  field_path: string;
  target: number;
  unit: string;
  visible: boolean;
  order: number;
}

interface KPIReport {
  id: string;
  name: string;
  period: string;
  createdAt: string;
}

const SERIES_COLORS: Record<string, string> = {
  cpu: '#3b82f6',
  memory: '#ef4444',
  net_in: '#22c55e',
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

export default function KPIPage() {
  const [kpiMetrics, setKpiMetrics] = useState<KPIMetric[]>([]);
  const [configs, setConfigs] = useState<KPIConfig[]>([]);
  const [history, setHistory] = useState<Record<string, (number | string)[]>>({});
  const [reports, setReports] = useState<KPIReport[]>([]);
  const [downloadFormats, setDownloadFormats] = useState<Record<string, 'csv' | 'json' | 'pdf'>>({});
  const [selectedMetric, setSelectedMetric] = useState<KPIMetric | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [newConfig, setNewConfig] = useState({
    name: '',
    endpoint: 'summary',
    field_path: '',
    target: 0,
    unit: '',
  });

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      try {
        const [valuesRes, configRes, historyRes] = await Promise.all([
          api.get('/api/v1/metrics/kpi/values'),
          api.get('/api/v1/metrics/kpi/config'),
          api.get('/api/v1/metrics/history'),
        ]);

        if (cancelled) return;

        setKpiMetrics(valuesRes.data?.data || []);
        setConfigs(configRes.data?.data || []);
        setHistory(historyRes.data || {});

        const createdAt = new Date().toISOString();
        setReports([
          {
            id: 'KPI-SNAP-001',
            name: 'KPI实时快照',
            period: 'month',
            createdAt,
          },
        ]);
      } catch (err) {
        console.error('KPI 数据加载失败', err);
      }
    };

    loadData();
    return () => { cancelled = true; };
  }, [refresh]);

  const getStatusInfo = (value: number, target: number) => {
    const ratio = value / target;
    if (ratio >= 1) {
      return { label: '达标', textColor: 'text-green-600', barColor: 'bg-green-500' };
    }
    if (ratio >= 0.9) {
      return { label: '未达标', textColor: 'text-orange-500', barColor: 'bg-orange-500' };
    }
    return { label: '未达标', textColor: 'text-red-600', barColor: 'bg-red-500' };
  };

  const handleViewReport = (report: KPIReport) => {
    const rows = kpiMetrics.map((m) => ({
      指标: m.name,
      当前值: `${m.value}${m.unit}`,
      目标值: `${m.target}${m.unit}`,
      状态: getStatusInfo(m.value, m.target).label,
    }));
    const html = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>${report.name}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; color: #1f2937; }
    h1 { font-size: 24px; margin-bottom: 8px; }
    .meta { color: #6b7280; margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; }
    th { background: #f9fafb; }
    .ok { color: #16a34a; }
    .fail { color: #dc2626; }
  </style>
</head>
<body>
  <h1>${report.name}</h1>
  <div class="meta">周期：${report.period} &nbsp;|&nbsp; 创建时间：${new Date(report.createdAt).toLocaleString()}</div>
  <table>
    <thead><tr><th>指标</th><th>当前值</th><th>目标值</th><th>状态</th></tr></thead>
    <tbody>
      ${rows.map((r) => `<tr><td>${r.指标}</td><td>${r.当前值}</td><td>${r.目标值}</td><td class="${r.状态 === '达标' ? 'ok' : 'fail'}">${r.状态}</td></tr>`).join('')}
    </tbody>
  </table>
</body>
</html>`;
    const win = window.open('', '_blank');
    if (win) {
      win.document.open();
      win.document.write(html);
      win.document.close();
    }
    return win;
  };

  const handleDownloadReport = (report: KPIReport, format: 'csv' | 'json' | 'pdf') => {
    const timestamp = new Date(report.createdAt).toISOString().slice(0, 19).replace(/[:T]/g, '-');
    const filename = `${report.name}-${timestamp}`;

    if (format === 'json') {
      const payload = {
        name: report.name,
        period: report.period,
        createdAt: report.createdAt,
        metrics: kpiMetrics,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename}.json`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }

    if (format === 'csv') {
      const headers = ['指标', '当前值', '目标值', '单位', '状态'];
      const rows = kpiMetrics.map((m) => {
        const s = getStatusInfo(m.value, m.target);
        return [m.name, m.value, m.target, m.unit, s.label].join(',');
      });
      const csv = [headers.join(','), ...rows].join('\n');
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }

    if (format === 'pdf') {
      const win = handleViewReport(report);
      if (win) {
        win.focus();
        setTimeout(() => win.print(), 500);
      }
    }
  };

  const handleConfigChange = (id: string, patch: Partial<KPIConfig>) => {
    setConfigs((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...patch } : c))
    );
  };

  const saveConfig = async (config: KPIConfig) => {
    try {
      await api.put(`/api/v1/metrics/kpi/config/${config.id}`, config);
      setRefresh((r) => r + 1);
    } catch (err) {
      console.error('保存 KPI 配置失败', err);
      alert('保存失败');
    }
  };

  const deleteConfig = async (id: string) => {
    if (!window.confirm('确定删除该 KPI 配置？')) return;
    try {
      await api.delete(`/api/v1/metrics/kpi/config/${id}`);
      setRefresh((r) => r + 1);
    } catch (err) {
      console.error('删除 KPI 配置失败', err);
      alert('删除失败');
    }
  };

  const createConfig = async () => {
    if (!newConfig.name || !newConfig.field_path || !newConfig.unit) {
      alert('请填写完整信息');
      return;
    }
    try {
      await api.post('/api/v1/metrics/kpi/config', {
        ...newConfig,
        target: Number(newConfig.target),
        visible: true,
        order: configs.length,
      });
      setNewConfig({ name: '', endpoint: 'summary', field_path: '', target: 0, unit: '' });
      setRefresh((r) => r + 1);
    } catch (err) {
      console.error('新增 KPI 配置失败', err);
      alert('新增失败');
    }
  };

  const chartSeries = useMemo(
    () =>
      Object.entries(history).filter(
        ([key, values]) =>
          !key.startsWith('_') &&
          key !== 'timestamps' &&
          Array.isArray(values) &&
          values.length > 0
      ),
    [history]
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
        <Button className="whitespace-nowrap" onClick={() => { const r = reports[0]; if (r) handleViewReport(r); }}>
          导出报告
        </Button>
      </div>

      {/* KPI 卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpiMetrics.map((metric) => {
          const status = getStatusInfo(metric.value, metric.target);
          return (
            <Card
              key={metric.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setSelectedMetric(metric)}
            >
              <CardHeader>
                <CardTitle className="text-sm">{metric.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold">{metric.value}</span>
                    <span className="text-sm text-gray-500">{metric.unit}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">目标: {metric.target}{metric.unit}</span>
                    <span className={status.textColor}>{status.label}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${status.barColor}`}
                      style={{ width: `${Math.min(100, (metric.value / metric.target) * 100)}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* 历史趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>KPI历史趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-gray-50 rounded-lg flex flex-col items-center justify-center p-4">
            {chartSeries.length === 0 ? (
              <p className="text-gray-500">暂无历史数据</p>
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

      {/* KPI 报告 */}
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
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => handleViewReport(report)}>
                        查看
                      </Button>
                      <Select
                        value={downloadFormats[report.id] || 'csv'}
                        onChange={(e) =>
                          setDownloadFormats((prev) => ({ ...prev, [report.id]: e.target.value as 'csv' | 'json' | 'pdf' }))
                        }
                        className="h-8 w-24 text-xs"
                      >
                        <option value="csv">CSV</option>
                        <option value="json">JSON</option>
                        <option value="pdf">PDF</option>
                      </Select>
                      <Button variant="outline" size="sm" onClick={() => handleDownloadReport(report, downloadFormats[report.id] || 'csv')}>
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

      {/* KPI 配置 */}
      <Card>
        <CardHeader>
          <CardTitle>KPI配置（后端持久化）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm text-gray-500">
            所有 KPI 定义、目标值、单位、数据源字段均保存在后端 data/kpi_config.json，可在此增删改查。
          </p>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-32">指标名称</TableHead>
                  <TableHead>数据源</TableHead>
                  <TableHead className="w-40">字段路径</TableHead>
                  <TableHead className="w-24">目标值</TableHead>
                  <TableHead className="w-20">单位</TableHead>
                  <TableHead className="w-16">显示</TableHead>
                  <TableHead className="w-40">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {configs.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <Input
                        value={c.name}
                        onChange={(e) => handleConfigChange(c.id, { name: e.target.value })}
                        className="h-8 text-xs"
                      />
                    </TableCell>
                    <TableCell>
                      <Select
                        value={c.endpoint}
                        onChange={(e) => handleConfigChange(c.id, { endpoint: e.target.value })}
                        className="h-8 text-xs"
                      >
                        <option value="summary">summary</option>
                        <option value="snapshot">snapshot</option>
                        <option value="agent/decision-accuracy">agent/decision-accuracy</option>
                        <option value="agent/feedback-accuracy">agent/feedback-accuracy</option>
                      </Select>
                    </TableCell>
                    <TableCell>
                      <Input
                        value={c.field_path}
                        onChange={(e) => handleConfigChange(c.id, { field_path: e.target.value })}
                        className="h-8 text-xs"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        value={c.target}
                        onChange={(e) => handleConfigChange(c.id, { target: Number(e.target.value) })}
                        className="h-8 text-xs"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        value={c.unit}
                        onChange={(e) => handleConfigChange(c.id, { unit: e.target.value })}
                        className="h-8 text-xs"
                      />
                    </TableCell>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={c.visible}
                        onChange={(e) => handleConfigChange(c.id, { visible: e.target.checked })}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => saveConfig(c)}>
                          保存
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => deleteConfig(c.id)}>
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end border-t pt-4">
            <Input
              placeholder="指标名称"
              value={newConfig.name}
              onChange={(e) => setNewConfig((p) => ({ ...p, name: e.target.value }))}
              className="h-8 text-xs"
            />
            <Select
              value={newConfig.endpoint}
              onChange={(e) => setNewConfig((p) => ({ ...p, endpoint: e.target.value }))}
              className="h-8 text-xs"
            >
              <option value="summary">summary</option>
              <option value="snapshot">snapshot</option>
              <option value="agent/decision-accuracy">agent/decision-accuracy</option>
              <option value="agent/feedback-accuracy">agent/feedback-accuracy</option>
            </Select>
            <Input
              placeholder="字段路径，如 cpu.usage_percent"
              value={newConfig.field_path}
              onChange={(e) => setNewConfig((p) => ({ ...p, field_path: e.target.value }))}
              className="h-8 text-xs"
            />
            <Input
              type="number"
              placeholder="目标值"
              value={newConfig.target}
              onChange={(e) => setNewConfig((p) => ({ ...p, target: Number(e.target.value) }))}
              className="h-8 text-xs"
            />
            <Input
              placeholder="单位"
              value={newConfig.unit}
              onChange={(e) => setNewConfig((p) => ({ ...p, unit: e.target.value }))}
              className="h-8 text-xs"
            />
            <Button onClick={createConfig} className="md:col-span-5 w-full md:w-auto">
              新增 KPI
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* KPI 详情弹窗 */}
      <Dialog open={!!selectedMetric} onOpenChange={(open) => !open && setSelectedMetric(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedMetric?.name} 详情</DialogTitle>
          </DialogHeader>
          {selectedMetric && (
            <div className="space-y-6">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold">{selectedMetric.value}</span>
                <span className="text-lg text-gray-500">{selectedMetric.unit}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">目标: {selectedMetric.target}{selectedMetric.unit}</span>
                {(() => {
                  const s = getStatusInfo(selectedMetric.value, selectedMetric.target);
                  return <span className={s.textColor}>{s.label}</span>;
                })()}
              </div>
              <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getStatusInfo(selectedMetric.value, selectedMetric.target).barColor}`}
                  style={{ width: `${Math.min(100, (selectedMetric.value / selectedMetric.target) * 100)}%` }}
                />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">历史趋势</h3>
                {(() => {
                  const values = history[selectedMetric.name];
                  if (!values || !Array.isArray(values) || values.length === 0) {
                    return <p className="text-sm text-gray-400">暂无历史数据</p>;
                  }
                  const nums = values.map((v) => parseMetricValue(v));
                  const max = Math.max(1, ...nums);
                  const w = 300;
                  const h = 100;
                  const points = nums
                    .map((v, i) => `${(i / (nums.length - 1 || 1)) * w},${h - (v / max) * h}`)
                    .join(' ');
                  return (
                    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-32 bg-gray-50 rounded-lg">
                      <polyline fill="none" stroke="#3b82f6" strokeWidth={2} points={points} />
                    </svg>
                  );
                })()}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
