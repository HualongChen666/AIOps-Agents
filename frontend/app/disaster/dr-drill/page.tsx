'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DrillRun {
  scenario: string;
  status: string;
  success?: boolean;
  start_time?: string;
  end_time?: string | null;
  duration_seconds?: number;
}

interface DrillData {
  status: string;
  current_drill: DrillRun | null;
  last_drill: DrillRun | null;
  drill_count: number;
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  completed: 'default',
  running: 'secondary',
  failed: 'destructive',
};

export default function DrDrillPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DrillData | null>(null);
  const [scenario, setScenario] = useState('database_failover');
  const [running, setRunning] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/dr-drill');
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载演练状态失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const startDrill = async () => {
    try {
      setRunning(true);
      const res = await api.post('/api/disaster/dr-drill', { scenario, parameters: {} });
      toast.success(`演练已执行：${res.data.drill_status}${res.data.success ? '（成功）' : ''}`);
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '启动演练失败');
    } finally {
      setRunning(false);
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

  const last = data?.last_drill;
  const current = data?.current_drill;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">灾难恢复演练</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">累计演练</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{data?.drill_count ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">当前演练</CardTitle></CardHeader><CardContent>{current ? <Badge variant={STATUS_VARIANT[current.status] ?? 'secondary'}>{current.status}</Badge> : <span className="text-gray-400">空闲</span>}</CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">上次结果</CardTitle></CardHeader><CardContent>{last ? <Badge variant={last.success ? 'default' : 'destructive'}>{last.success ? '成功' : '失败'}</Badge> : <span className="text-gray-400">无</span>}</CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>启动演练</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="w-64">
            <label className="text-sm text-gray-600">演练场景</label>
            <Select value={scenario} onValueChange={setScenario}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="database_failover">数据库故障转移</SelectItem>
                <SelectItem value="region_failure">区域故障</SelectItem>
                <SelectItem value="data_corruption">数据损坏</SelectItem>
                <SelectItem value="network_partition">网络分区</SelectItem>
                <SelectItem value="service_outage">服务中断</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={startDrill} disabled={running}>{running ? '演练中...' : '启动演练'}</Button>
        </CardContent>
      </Card>

      {last && (
        <Card>
          <CardHeader><CardTitle>上次演练详情</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-gray-600">场景:</span> {last.scenario}</div>
            <div><span className="text-gray-600">状态:</span> {last.status}</div>
            <div><span className="text-gray-600">耗时:</span> {last.duration_seconds?.toFixed(1) ?? '—'}s</div>
            <div><span className="text-gray-600">开始:</span> {last.start_time ? new Date(last.start_time).toLocaleString() : '—'}</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
