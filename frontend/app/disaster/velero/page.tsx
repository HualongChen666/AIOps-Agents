'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface VeleroStatus {
  status: string;
  velero_enabled: boolean;
  velero_available: boolean;
  backup_location: string | null;
  last_backup: string | null;
  schedule: string | null;
}

export default function VeleroPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<VeleroStatus | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/velero');
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载 Velero 状态失败');
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Velero 备份</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">启用状态</CardTitle></CardHeader><CardContent><Badge variant={data?.velero_enabled ? 'default' : 'secondary'}>{data?.velero_enabled ? '已启用' : '已停用'}</Badge></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">工具可用性</CardTitle></CardHeader><CardContent><Badge variant={data?.velero_available ? 'default' : 'destructive'}>{data?.velero_available ? '可用' : '不可用'}</Badge></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">调度</CardTitle></CardHeader><CardContent><div className="text-lg font-bold">{data?.schedule ?? '—'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>备份详情</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div><span className="text-gray-600">备份位置:</span> {data?.backup_location ?? '—'}</div>
          <div><span className="text-gray-600">最近备份:</span> {data?.last_backup ? new Date(data.last_backup).toLocaleString() : '无'}</div>
        </CardContent>
      </Card>

      {!data?.velero_available && (
        <div className="text-sm text-amber-600">Velero CLI 不可用，请确认已在集群中安装 Velero 并暴露 CLI。</div>
      )}
    </div>
  );
}
