'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface RecoveryStatus {
  status: string;
  recoverable_backups: number;
  last_recovery: string | null;
  recovery_status: string;
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  ready: 'default',
  warning: 'secondary',
  no_backups: 'destructive',
};

export default function BackupRecoveryPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [form, setForm] = useState({ backup_file: '', restore_type: 'database' });
  const [restoring, setRestoring] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/backup-recovery');
      setStatus(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载恢复状态失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const restore = async () => {
    if (!form.backup_file.trim()) {
      toast.error('请填写备份文件路径');
      return;
    }
    try {
      setRestoring(true);
      const res = await api.post('/api/disaster/restore', form);
      if (res.data.restored) {
        toast.success(`恢复完成：${res.data.restore_type}`);
      } else {
        toast.error('恢复未成功，请检查备份文件');
      }
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '恢复失败');
    } finally {
      setRestoring(false);
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
        <h1 className="text-3xl font-bold text-gray-900">备份恢复</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">可恢复备份</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{status?.recoverable_backups ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">恢复状态</CardTitle></CardHeader><CardContent><Badge variant={STATUS_VARIANT[status?.recovery_status ?? ''] ?? 'secondary'}>{status?.recovery_status ?? 'unknown'}</Badge></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">最近恢复</CardTitle></CardHeader><CardContent><div className="text-sm">{status?.last_recovery ? new Date(status.last_recovery).toLocaleString() : '无'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>执行恢复</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[260px]">
            <Label htmlFor="file">备份文件路径</Label>
            <Input id="file" value={form.backup_file} onChange={(e) => setForm({ ...form, backup_file: e.target.value })} placeholder="/backups/db_backup_xxx.sql" className="mt-1" />
          </div>
          <div className="w-48">
            <Label>恢复类型</Label>
            <Select value={form.restore_type} onValueChange={(v) => setForm({ ...form, restore_type: v })}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="database">数据库</SelectItem>
                <SelectItem value="redis">Redis</SelectItem>
                <SelectItem value="configuration">配置</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={restore} disabled={restoring}>{restoring ? '恢复中...' : '执行恢复'}</Button>
        </CardContent>
      </Card>
    </div>
  );
}
