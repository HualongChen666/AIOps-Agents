'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface TrafficRule {
  id: string;
  name: string;
  service_name: string;
  weight: number;
  timeout_seconds: number;
  enabled: boolean;
}

export default function TrafficManagementPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rules, setRules] = useState<TrafficRule[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', service_name: '', version: 'v1', host: '', weight: 100, timeout_seconds: 30 });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/traffic');
      setRules(res.data.data?.traffic_rules || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载流量规则失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim() || !form.service_name.trim()) {
      toast.error('请填写规则名称和目标服务');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/service-mesh/traffic', {
        name: form.name,
        service_name: form.service_name,
        match_conditions: { headers: { version: form.version } },
        destination: { host: form.host || form.service_name, subset: form.version },
        weight: form.weight,
        timeout_seconds: form.timeout_seconds,
      });
      toast.success('流量规则已创建');
      setForm({ name: '', service_name: '', version: 'v1', host: '', weight: 100, timeout_seconds: 30 });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/api/v1/service-mesh/traffic/${id}`);
      toast.success('规则已删除');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '删除失败');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">流量管理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>新建流量规则</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div><Label htmlFor="tr-name">规则名称</Label><Input id="tr-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="tr-svc">目标服务</Label><Input id="tr-svc" value={form.service_name} onChange={(e) => setForm({ ...form, service_name: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="tr-ver">匹配版本</Label><Input id="tr-ver" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="tr-host">目标主机</Label><Input id="tr-host" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} placeholder="默认同服务名" className="mt-1" /></div>
          <div><Label htmlFor="tr-w">权重</Label><Input id="tr-w" type="number" value={form.weight} onChange={(e) => setForm({ ...form, weight: Number(e.target.value) || 0 })} className="mt-1" /></div>
          <div><Label htmlFor="tr-to">超时(秒)</Label><Input id="tr-to" type="number" value={form.timeout_seconds} onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) || 0 })} className="mt-1" /></div>
          <div className="flex items-end"><Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建规则'}</Button></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>流量规则（{rules.length}）</CardTitle></CardHeader>
        <CardContent>
          {rules.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无流量规则</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-600">
                  <th className="py-2">名称</th><th className="py-2">服务</th><th className="py-2">权重</th>
                  <th className="py-2">超时</th><th className="py-2">状态</th><th className="py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id} className="border-b">
                    <td className="py-2">{r.name}</td>
                    <td className="py-2">{r.service_name}</td>
                    <td className="py-2">{r.weight}%</td>
                    <td className="py-2">{r.timeout_seconds}s</td>
                    <td className="py-2"><Badge variant={r.enabled ? 'default' : 'secondary'}>{r.enabled ? '启用' : '停用'}</Badge></td>
                    <td className="py-2"><Button size="sm" variant="secondary" onClick={() => remove(r.id)}>删除</Button></td>
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
