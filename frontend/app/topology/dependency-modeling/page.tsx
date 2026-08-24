'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Dependency {
  id: string;
  source: string;
  target: string;
  type: 'sync' | 'async' | 'weak';
  strength: number;
  description: string;
}

export default function DependencyModelingPage() {
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newDep, setNewDep] = useState({
    source: '',
    target: '',
    type: 'sync' as const,
    strength: 1,
    description: ''
  });

  useEffect(() => {
    fetchDependencies();
  }, []);

  const fetchDependencies = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/dependency-modeling');
      setDependencies(res.data.dependencies || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载依赖模型失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    try {
      await api.post('/api/topology/dependency-modeling', newDep);
      setNewDep({ source: '', target: '', type: 'sync', strength: 1, description: '' });
      fetchDependencies();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '添加依赖失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/api/topology/dependency-modeling/${id}`);
      fetchDependencies();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除依赖失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchDependencies} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">依赖建模</h1>
        <Button onClick={fetchDependencies}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>添加依赖关系</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="源服务"
              value={newDep.source}
              onChange={(e) => setNewDep({ ...newDep, source: e.target.value })}
            />
            <Input
              placeholder="目标服务"
              value={newDep.target}
              onChange={(e) => setNewDep({ ...newDep, target: e.target.value })}
            />
            <Input
              placeholder="描述"
              value={newDep.description}
              onChange={(e) => setNewDep({ ...newDep, description: e.target.value })}
            />
            <Input
              type="number"
              placeholder="依赖强度 (1-10)"
              value={newDep.strength}
              onChange={(e) => setNewDep({ ...newDep, strength: parseInt(e.target.value) || 1 })}
            />
          </div>
          <Button onClick={handleAdd} className="mt-4">添加</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>依赖关系列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dependencies.map((dep) => (
              <div key={dep.id} className="border rounded-lg p-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold">{dep.source}</span>
                    <span className="text-gray-400">→</span>
                    <span className="font-semibold">{dep.target}</span>
                    <Badge variant="outline">{dep.type}</Badge>
                    <Badge variant="secondary">强度: {dep.strength}</Badge>
                  </div>
                  <div className="text-sm text-gray-600">{dep.description}</div>
                </div>
                <Button variant="destructive" size="sm" onClick={() => handleDelete(dep.id)}>
                  删除
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
