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

interface Fault {
  id: string;
  name: string;
  description: string | null;
  fault_type: string;
  target: string | null;
  severity: string;
  status: string | null;
  created_at: string | null;
}

const FAULT_TYPES = [
  'network_latency',
  'disk_failure',
  'cpu_overload',
  'memory_leak',
  'service_crash',
  'database_error',
  'cache_failure',
  'network_partition',
];

export default function FaultInjectionPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [faults, setFaults] = useState<Fault[]>([]);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', fault_type: 'network_latency', severity: 'high', description: '' });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/chaos/faults', { params: { limit: 100 } });
      setFaults(res.data.data?.items || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载故障注入失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const createFault = async () => {
    if (!form.name.trim()) {
      toast.error('请填写故障名称');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/chaos/faults', {
        name: form.name,
        fault_type: form.fault_type,
        description: form.description || null,
        parameters: {},
        severity: form.severity,
      });
      toast.success('故障已登记');
      setForm({ name: '', fault_type: 'network_latency', severity: 'high', description: '' });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建故障失败');
    } finally {
      setCreating(false);
    }
  };

  const inject = async (id: string) => {
    try {
      setBusyId(id);
      const res = await api.post(`/api/v1/chaos/faults/${id}/inject`);
      toast.success(`故障已注入：${res.data.message || 'ok'}`);
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '注入失败');
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (id: string) => {
    try {
      setBusyId(id);
      await api.delete(`/api/v1/chaos/faults/${id}`);
      toast.success('故障已删除');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '删除失败');
    } finally {
      setBusyId(null);
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
        <h1 className="text-3xl font-bold text-gray-900">故障注入</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>登记故障</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="fname">故障名称</Label>
              <Input id="fname" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" />
            </div>
            <div>
              <Label>故障类型</Label>
              <Select value={form.fault_type} onValueChange={(v) => setForm({ ...form, fault_type: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FAULT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>严重程度</Label>
              <Select value={form.severity} onValueChange={(v) => setForm({ ...form, severity: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">低</SelectItem>
                  <SelectItem value="medium">中</SelectItem>
                  <SelectItem value="high">高</SelectItem>
                  <SelectItem value="critical">严重</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-3">
              <Label htmlFor="fdesc">描述</Label>
              <Input id="fdesc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1" />
            </div>
          </div>
          <Button onClick={createFault} disabled={creating}>{creating ? '创建中...' : '登记故障'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>故障列表（{faults.length}）</CardTitle></CardHeader>
        <CardContent>
          {faults.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无故障</div>
          ) : (
            <div className="space-y-3">
              {faults.map((f) => (
                <div key={f.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{f.name}</span>
                      <Badge variant="secondary">{f.fault_type}</Badge>
                      <Badge variant={f.severity === 'high' || f.severity === 'critical' ? 'destructive' : 'secondary'}>{f.severity}</Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => inject(f.id)} disabled={busyId === f.id}>注入</Button>
                      <Button size="sm" variant="secondary" onClick={() => remove(f.id)} disabled={busyId === f.id}>删除</Button>
                    </div>
                  </div>
                  {f.description && <div className="text-sm text-gray-600">{f.description}</div>}
                  <div className="text-xs text-gray-400 mt-1">ID: {f.id} | 状态: {f.status || '未注入'}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
