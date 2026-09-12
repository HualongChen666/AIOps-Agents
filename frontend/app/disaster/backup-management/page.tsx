'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface BackupOverview {
  status: string;
  backup_count: number;
  total_size_mb: number;
  last_backup: string | null;
  retention_days: number;
  backup_dir: string;
  message?: string;
}

export default function BackupManagementPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<BackupOverview | null>(null);
  const [backupType, setBackupType] = useState('database');
  const [running, setRunning] = useState(false);
  const [cleaning, setCleaning] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/backup-management');
      setOverview(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载备份概览失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const runBackup = async () => {
    try {
      setRunning(true);
      const res = await api.post('/api/disaster/backup', {
        backup_type: backupType,
        description: `Manual backup from console (${backupType})`,
      });
      toast.success(`备份完成：${res.data.backup_file}`);
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '备份执行失败');
    } finally {
      setRunning(false);
    }
  };

  const cleanup = async () => {
    try {
      setCleaning(true);
      const res = await api.delete('/api/disaster/backups');
      toast.success(`已清理 ${res.data.deleted_count} 个过期备份`);
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '清理失败');
    } finally {
      setCleaning(false);
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
        <h1 className="text-3xl font-bold text-gray-900">备份管理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">备份数量</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{overview?.backup_count ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">总大小</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{(overview?.total_size_mb ?? 0).toFixed(2)} MB</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">保留天数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{overview?.retention_days ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">最近备份</CardTitle></CardHeader><CardContent><div className="text-sm font-medium">{overview?.last_backup ? new Date(overview.last_backup).toLocaleString() : '无'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>备份目录</CardTitle></CardHeader>
        <CardContent>
          <div className="font-mono text-sm">{overview?.backup_dir}</div>
          {overview?.message && <div className="text-sm text-amber-600 mt-2">{overview.message}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>执行操作</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="w-56">
            <label className="text-sm text-gray-600">备份类型</label>
            <Select value={backupType} onValueChange={setBackupType}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="database">数据库</SelectItem>
                <SelectItem value="redis">Redis</SelectItem>
                <SelectItem value="configuration">配置</SelectItem>
                <SelectItem value="all">全部</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={runBackup} disabled={running}>{running ? '备份中...' : '立即备份'}</Button>
          <Button variant="secondary" onClick={cleanup} disabled={cleaning}>{cleaning ? '清理中...' : '清理过期备份'}</Button>
        </CardContent>
      </Card>
    </div>
  );
}
