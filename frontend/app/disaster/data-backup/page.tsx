'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DataBackupStatus {
  status: string;
  database_backups: number;
  redis_backups: number;
  config_backups: number;
  total_backups: number;
  last_data_backup: string | null;
}

export default function DataBackupPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DataBackupStatus | null>(null);
  const [running, setRunning] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/data-backup');
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据备份状态失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const backupAll = async () => {
    try {
      setRunning(true);
      await api.post('/api/disaster/backup', { backup_type: 'all', description: 'Full data backup' });
      toast.success('全量数据备份完成');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '备份失败');
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

  const items = [
    { label: '数据库备份', value: data?.database_backups ?? 0 },
    { label: 'Redis 备份', value: data?.redis_backups ?? 0 },
    { label: '配置备份', value: data?.config_backups ?? 0 },
    { label: '备份总数', value: data?.total_backups ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据备份</h1>
        <div className="flex gap-2">
          <Button onClick={backupAll} disabled={running}>{running ? '备份中...' : '备份全部数据'}</Button>
          <Button variant="secondary" onClick={fetchData}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {items.map((it) => (
          <Card key={it.label}>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">{it.label}</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold">{it.value}</div></CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>最近数据备份</CardTitle></CardHeader>
        <CardContent>
          <div className="text-sm">{data?.last_data_backup ? new Date(data.last_data_backup).toLocaleString() : '暂无备份记录'}</div>
        </CardContent>
      </Card>
    </div>
  );
}
