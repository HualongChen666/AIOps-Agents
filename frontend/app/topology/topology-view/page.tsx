'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';

interface TopologyView {
  id: string;
  name: string;
  layout: 'tree' | 'force' | 'circular';
  zoom: number;
  filter: string;
}

export default function TopologyViewPage() {
  const [view, setView] = useState<TopologyView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layout, setLayout] = useState('tree');

  useEffect(() => {
    fetchView();
  }, [layout]);

  const fetchView = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/api/topology/view?layout=${layout}`);
      setView(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载拓扑视图失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchView} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑视图</h1>
        <div className="flex gap-2">
          <Select value={layout} onChange={(e) => setLayout(e.target.value)}>
            <option value="tree">树形布局</option>
            <option value="force">力导向布局</option>
            <option value="circular">环形布局</option>
          </Select>
          <Button onClick={fetchView}>刷新</Button>
        </div>
      </div>

      {view && (
        <Card>
          <CardHeader>
            <CardTitle>{view.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
              <div className="text-gray-500">拓扑可视化区域</div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">缩放</label>
                <div className="text-sm">{Math.round(view.zoom * 100)}%</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">过滤器</label>
                <div className="text-sm">{view.filter || '无'}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
