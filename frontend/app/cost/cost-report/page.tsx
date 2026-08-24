'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CostReport {
  id: string;
  period_start: string;
  period_end: string;
  total_cost: number;
  budget: number;
  variance: number;
  by_service: Array<{ service: string; cost: number }>;
  by_category: Array<{ category: string; cost: number }>;
  trends: Array<{ date: string; cost: number }>;
}

export default function CostReportPage() {
  const [report, setReport] = useState<CostReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState('30d');

  const generateReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/cost/cost-report', { period });
      setReport(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '生成报告失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    generateReport();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">成本报告</h1>
        <div className="flex gap-2">
          <Input
            placeholder="报告周期"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="w-40"
          />
          <Button onClick={generateReport} disabled={loading}>
            {loading ? '生成中...' : '生成报告'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {report && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>报告概览</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <div className="p-4 border rounded-lg">
                  <div className="text-2xl font-bold">${report.total_cost.toFixed(2)}</div>
                  <div className="text-sm text-gray-500">总成本</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-2xl font-bold">${report.budget.toFixed(2)}</div>
                  <div className="text-sm text-gray-500">预算</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className={`text-2xl font-bold ${report.variance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                    ${Math.abs(report.variance).toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-500">
                    {report.variance > 0 ? '超支' : '节省'}
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-2xl font-bold">
                    {new Date(report.period_start).toLocaleDateString()}
                  </div>
                  <div className="text-sm text-gray-500">开始日期</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>按服务分类</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {report.by_service.map((item) => (
                    <div key={item.service} className="flex items-center justify-between">
                      <span>{item.service}</span>
                      <span className="font-semibold">${item.cost.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>按类别分类</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {report.by_category.map((item) => (
                    <div key={item.category} className="flex items-center justify-between">
                      <span>{item.category}</span>
                      <span className="font-semibold">${item.cost.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>成本趋势</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 flex items-end gap-2">
                {report.trends.map((trend) => (
                  <div
                    key={trend.date}
                    className="flex-1 bg-blue-500 rounded-t"
                    style={{ height: `${(trend.cost / Math.max(...report.trends.map(t => t.cost))) * 100}%` }}
                    title={`${trend.date}: $${trend.cost.toFixed(2)}`}
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
