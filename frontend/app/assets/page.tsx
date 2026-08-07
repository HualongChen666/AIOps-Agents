'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';

interface Asset {
  id: number;
  name: string;
  service?: string;
  business_unit?: string;
  env?: string;
  owner?: string;
  created_at?: string;
}

const emptyForm = { name: '', service: '', business_unit: '', env: '', owner: '' };

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(false);

  const loadAssets = async () => {
    try {
      const res = await api.get('/api/v1/assets');
      setAssets(res.data || []);
    } catch {
      setAssets([]);
    }
  };

  useEffect(() => {
    loadAssets();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setLoading(true);
    try {
      await api.post('/api/v1/assets', {
        name: form.name,
        service: form.service || undefined,
        business_unit: form.business_unit || undefined,
        env: form.env || undefined,
        owner: form.owner || undefined,
      });
      setForm(emptyForm);
      await loadAssets();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('确定删除该资产吗？')) return;
    try {
      await api.delete(`/api/v1/assets/${id}`);
      await loadAssets();
    } catch {
      // toast handled by api.ts
    }
  };

  return (
    <main className="p-6 space-y-6 bg-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold text-gray-900">资产（监控目标）管理</h1>

      <Card>
        <CardHeader><CardTitle>新增资产</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Input placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input placeholder="服务标识 service" value={form.service} onChange={(e) => setForm({ ...form, service: e.target.value })} />
            <Input placeholder="业务单元" value={form.business_unit} onChange={(e) => setForm({ ...form, business_unit: e.target.value })} />
            <Input placeholder="环境" value={form.env} onChange={(e) => setForm({ ...form, env: e.target.value })} />
            <Button type="submit" disabled={loading}>{loading ? '创建中...' : '创建'}</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>资产列表</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>业务单元</TableHead>
                <TableHead>环境</TableHead>
                <TableHead>负责人</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assets.map((asset) => (
                <TableRow key={asset.id}>
                  <TableCell>{asset.id}</TableCell>
                  <TableCell className="font-medium">{asset.name}</TableCell>
                  <TableCell>{asset.service || '-'}</TableCell>
                  <TableCell>{asset.business_unit || '-'}</TableCell>
                  <TableCell>{asset.env || '-'}</TableCell>
                  <TableCell>{asset.owner || '-'}</TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" onClick={() => handleDelete(asset.id)}>删除</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </main>
  );
}
