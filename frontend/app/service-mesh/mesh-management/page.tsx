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

interface MeshConfig {
  id: string;
  name: string;
  mesh_type: string;
  namespace: string;
  profile: string;
  auto_injection_enabled: boolean;
  mtls_enabled: boolean;
  status: string;
}

export default function MeshManagementPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [configs, setConfigs] = useState<MeshConfig[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', mesh_type: 'istio', namespace: 'istio-system', profile: 'default', auto_injection_enabled: true, mtls_enabled: true });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/configurations');
      setConfigs(res.data.data?.configurations || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载网格配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim()) {
      toast.error('请填写配置名称');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/service-mesh/configurations', form);
      toast.success('网格配置已创建');
      setForm({ name: '', mesh_type: 'istio', namespace: 'istio-system', profile: 'default', auto_injection_enabled: true, mtls_enabled: true });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/api/v1/service-mesh/configurations/${id}`);
      toast.success('配置已删除');
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
        <h1 className="text-3xl font-bold text-gray-900">网格管理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>新建网格配置</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div><Label htmlFor="mm-name">名称</Label><Input id="mm-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
            <div>
              <Label>网格类型</Label>
              <Select value={form.mesh_type} onValueChange={(v) => setForm({ ...form, mesh_type: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="istio">Istio</SelectItem>
                  <SelectItem value="linkerd">Linkerd</SelectItem>
                  <SelectItem value="consul">Consul</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label htmlFor="mm-ns">命名空间</Label><Input id="mm-ns" value={form.namespace} onChange={(e) => setForm({ ...form, namespace: e.target.value })} className="mt-1" /></div>
            <div><Label htmlFor="mm-prof">配置档</Label><Input id="mm-prof" value={form.profile} onChange={(e) => setForm({ ...form, profile: e.target.value })} className="mt-1" /></div>
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.auto_injection_enabled} onChange={(e) => setForm({ ...form, auto_injection_enabled: e.target.checked })} />自动注入</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.mtls_enabled} onChange={(e) => setForm({ ...form, mtls_enabled: e.target.checked })} />mTLS</label>
          </div>
          <Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建配置'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>网格配置（{configs.length}）</CardTitle></CardHeader>
        <CardContent>
          {configs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无网格配置</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-600">
                  <th className="py-2">名称</th><th className="py-2">类型</th><th className="py-2">命名空间</th>
                  <th className="py-2">自动注入</th><th className="py-2">mTLS</th><th className="py-2">状态</th><th className="py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((c) => (
                  <tr key={c.id} className="border-b">
                    <td className="py-2 font-medium">{c.name}</td>
                    <td className="py-2">{c.mesh_type}</td>
                    <td className="py-2">{c.namespace}</td>
                    <td className="py-2">{c.auto_injection_enabled ? '是' : '否'}</td>
                    <td className="py-2">{c.mtls_enabled ? '是' : '否'}</td>
                    <td className="py-2"><Badge variant={c.status === 'active' ? 'default' : 'secondary'}>{c.status}</Badge></td>
                    <td className="py-2"><Button size="sm" variant="secondary" onClick={() => remove(c.id)}>删除</Button></td>
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
