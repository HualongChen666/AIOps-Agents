'use client'

import { useState } from 'react';
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

export default function KPIPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [kpiMetrics, setKpiMetrics] = useState<KPIMetric[]>([
    { name: '系统可用性', value: 99.95, target: 99.9, unit: '%', trend: 'up' },
    { name: 'MTTR', value: 15, target: 30, unit: '分钟', trend: 'down' },
    { name: 'MTBF', value: 720, target: 720, unit: '小时', trend: 'stable' },
    { name: '告警响应时间', value: 5, target: 10, unit: '分钟', trend: 'down' },
    { name: '自动修复成功率', value: 87, target: 85, unit: '%', trend: 'up' },
    { name: 'SLA达成率', value: 98.5, target: 95, unit: '%', trend: 'up' },
  ]);

  const [reports, setReports] = useState<KPIReport[]>([
    {
      id: 'KPI-001',
      name: '2024年1月KPI报告',
      period: '2024-01',
      createdAt: new Date().toISOString(),
    },
    {
      id: 'KPI-002',
      name: '2023年12月KPI报告',
      period: '2023-12',
      createdAt: new Date(Date.now() - 2592000000).toISOString(),
    },
  ]);

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
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">KPI历史趋势图 (使用ECharts渲染)</p>
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
