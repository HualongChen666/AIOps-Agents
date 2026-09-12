'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface Scenario {
  name: string;
  description: string;
  enabled: boolean;
}

export default function DrScenariosPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runningName, setRunningName] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/dr-scenarios');
      setScenarios(res.data.scenarios || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载场景失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const runScenario = async (name: string) => {
    try {
      setRunningName(name);
      const res = await api.post('/api/disaster/dr-drill', { scenario: name, parameters: {} });
      toast.success(`${name} 演练完成：${res.data.drill_status}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '演练失败');
    } finally {
      setRunningName(null);
    }
  };

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">灾难恢复场景</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>可用场景（{scenarios.length}）</CardTitle></CardHeader>
        <CardContent>
          {scenarios.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无场景</div>
          ) : (
            <div className="space-y-3">
              {scenarios.map((s) => (
                <div key={s.name} className="border rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{s.name}</div>
                    <div className="text-sm text-gray-500">{s.description}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={s.enabled ? 'default' : 'secondary'}>{s.enabled ? '启用' : '停用'}</Badge>
                    <Button size="sm" onClick={() => runScenario(s.name)} disabled={runningName === s.name}>
                      {runningName === s.name ? '执行中...' : '执行演练'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
