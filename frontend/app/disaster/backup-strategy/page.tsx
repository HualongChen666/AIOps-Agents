'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface BackupStrategy {
  backup_type: string;
  schedule: string;
  retention_days: number;
  compression_enabled: boolean;
  encryption_enabled: boolean;
  incremental_enabled: boolean;
}

export default function BackupStrategyPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<BackupStrategy | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/backup-strategy');
      setStrategy(res.data.strategy);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载备份策略失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const save = async () => {
    if (!strategy) return;
    try {
      setSaving(true);
      const res = await api.put('/api/disaster/backup-strategy', strategy);
      setStrategy(res.data.strategy);
      toast.success('备份策略已更新');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error || !strategy) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error || '无备份策略'}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">备份策略</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>策略配置</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>备份类型</Label>
              <Select value={strategy.backup_type} onValueChange={(v) => setStrategy({ ...strategy, backup_type: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">全量 (full)</SelectItem>
                  <SelectItem value="incremental">增量 (incremental)</SelectItem>
                  <SelectItem value="differential">差异 (differential)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>调度周期</Label>
              <Select value={strategy.schedule} onValueChange={(v) => setStrategy({ ...strategy, schedule: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">每日</SelectItem>
                  <SelectItem value="weekly">每周</SelectItem>
                  <SelectItem value="monthly">每月</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="retention">保留天数</Label>
              <Input id="retention" type="number" value={strategy.retention_days} onChange={(e) => setStrategy({ ...strategy, retention_days: Number(e.target.value) || 0 })} className="mt-1" />
            </div>
          </div>

          {(
            [
              ['compression_enabled', '启用压缩'],
              ['encryption_enabled', '启用加密'],
              ['incremental_enabled', '启用增量备份'],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="flex items-center justify-between border-t pt-3">
              <Label htmlFor={key}>{label}</Label>
              <input id={key} type="checkbox" checked={strategy[key]} onChange={(e) => setStrategy({ ...strategy, [key]: e.target.checked })} />
            </div>
          ))}

          <Button onClick={save} disabled={saving}>{saving ? '保存中...' : '保存策略'}</Button>
        </CardContent>
      </Card>
    </div>
  );
}
