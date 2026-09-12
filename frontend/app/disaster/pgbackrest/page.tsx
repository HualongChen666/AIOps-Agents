'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface PgBackRestStatus {
  status: string;
  pgbackrest_enabled: boolean;
  pgbackrest_available: boolean;
  repo_count: number;
  last_backup: string | null;
  backup_type: string | null;
}

export default function PgBackRestPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PgBackRestStatus | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/pgbackrest');
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载 pgBackRest 状态失败');
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
        <h1 className="text-3xl font-bold text-gray-900">pgBackRest 备份</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">启用状态</CardTitle></CardHeader><CardContent><Badge variant={data?.pgbackrest_enabled ? 'default' : 'secondary'}>{data?.pgbackrest_enabled ? '已启用' : '已停用'}</Badge></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">工具可用性</CardTitle></CardHeader><CardContent><Badge variant={data?.pgbackrest_available ? 'default' : 'destructive'}>{data?.pgbackrest_available ? '可用' : '不可用'}</Badge></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">仓库数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{data?.repo_count ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">备份类型</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{data?.backup_type ?? '—'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>最近备份</CardTitle></CardHeader>
        <CardContent>
          <div className="text-sm">{data?.last_backup ? new Date(data.last_backup).toLocaleString() : '暂无备份记录'}</div>
          {!data?.pgbackrest_available && (
            <div className="text-sm text-amber-600 mt-2">pgBackRest 二进制不可用，请确认已安装并纳入 PATH。</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
