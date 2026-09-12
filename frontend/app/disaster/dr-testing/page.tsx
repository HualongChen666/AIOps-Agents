'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';

interface TestResult {
  scenario: string;
  success: boolean;
  status: string;
  last_test: string;
  duration_seconds: number;
}

interface TestPayload {
  status: string;
  test_results: TestResult[];
  success_rate: number;
  total_tests: number;
  successful_tests: number;
}

export default function DrTestingPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TestPayload | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/dr-testing');
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载测试结果失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  const results = data?.test_results ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">灾难恢复测试</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader><CardTitle>成功率</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={data?.success_rate ?? 0} title="DR 测试" unit="%" color="#10b981" />
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">测试总数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{data?.total_tests ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">成功数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-green-600">{data?.successful_tests ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">失败数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{(data?.total_tests ?? 0) - (data?.successful_tests ?? 0)}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>测试结果明细</CardTitle></CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无测试记录，请先执行 DR 演练</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-600">
                  <th className="py-2">场景</th>
                  <th className="py-2">状态</th>
                  <th className="py-2">结果</th>
                  <th className="py-2">耗时</th>
                  <th className="py-2">测试时间</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={`${r.scenario}-${i}`} className="border-b">
                    <td className="py-2 font-mono">{r.scenario}</td>
                    <td className="py-2"><Badge variant="secondary">{r.status}</Badge></td>
                    <td className="py-2">
                      <Badge variant={r.success ? 'default' : 'destructive'}>{r.success ? '成功' : '失败'}</Badge>
                    </td>
                    <td className="py-2">{r.duration_seconds?.toFixed(1) ?? '—'}s</td>
                    <td className="py-2">{r.last_test ? new Date(r.last_test).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
