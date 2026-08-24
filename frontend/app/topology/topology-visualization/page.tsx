'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface VisualizationConfig {
  id: string;
  name: string;
  node_color: string;
  edge_color: string;
  show_labels: boolean;
  show_metrics: boolean;
  auto_refresh: boolean;
}

export default function TopologyVisualizationPage() {
  const [config, setConfig] = useState<VisualizationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/visualization');
      setConfig(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载可视化配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    try {
      await api.put('/api/topology/visualization', config);
      alert('配置已保存');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '保存配置失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchConfig} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑可视化</h1>
        <Button onClick={fetchConfig}>刷新</Button>
      </div>

      {config && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>可视化配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>显示标签</span>
                  <Badge variant={config.show_labels ? 'default' : 'secondary'}>
                    {config.show_labels ? '是' : '否'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>显示指标</span>
                  <Badge variant={config.show_metrics ? 'default' : 'secondary'}>
                    {config.show_metrics ? '是' : '否'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>自动刷新</span>
                  <Badge variant={config.auto_refresh ? 'default' : 'secondary'}>
                    {config.auto_refresh ? '是' : '否'}
                  </Badge>
                </div>
                <Button onClick={handleSave}>保存配置</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>拓扑图</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-gray-500">拓扑可视化渲染区域</div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
