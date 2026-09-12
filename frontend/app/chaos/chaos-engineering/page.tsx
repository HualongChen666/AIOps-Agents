'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import api from '@/lib/api';

interface ChaosStatus {
  enabled: boolean;
  stats: Record<string, unknown>;
}

interface Template {
  id: string;
  name: string;
  type: string;
  description: string;
  severity: string;
}

export default function ChaosEngineeringPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<ChaosStatus | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [sRes, tRes] = await Promise.all([
        api.get('/api/v1/chaos/status'),
        api.get('/api/v1/chaos/templates'),
      ]);
      setStatus(sRes.data.data);
      setTemplates(tRes.data.data?.templates || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载混沌工程信息失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900">混沌工程</h1>
          <Badge variant={status?.enabled ? 'default' : 'secondary'}>{status?.enabled ? '引擎已启用' : '引擎已停用'}</Badge>
        </div>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link href="/chaos/chaos-experiments"><Card className="cursor-pointer hover:shadow-md"><CardHeader><CardTitle>实验管理</CardTitle></CardHeader><CardContent className="text-sm text-gray-500">执行与查看混沌实验</CardContent></Card></Link>
        <Link href="/chaos/chaos-scenarios"><Card className="cursor-pointer hover:shadow-md"><CardHeader><CardTitle>场景编排</CardTitle></CardHeader><CardContent className="text-sm text-gray-500">组合多个实验批量执行</CardContent></Card></Link>
        <Link href="/chaos/fault-injection"><Card className="cursor-pointer hover:shadow-md"><CardHeader><CardTitle>故障注入</CardTitle></CardHeader><CardContent className="text-sm text-gray-500">登记并注入故障</CardContent></Card></Link>
        <Link href="/chaos/chaos-dashboard"><Card className="cursor-pointer hover:shadow-md"><CardHeader><CardTitle>仪表盘</CardTitle></CardHeader><CardContent className="text-sm text-gray-500">整体指标与分布</CardContent></Card></Link>
      </div>

      <Card>
        <CardHeader><CardTitle>支持的实验类型</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {templates.map((t) => (
              <div key={t.id} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary">{t.type}</Badge>
                  <span className="font-medium">{t.name}</span>
                  <Badge variant={t.severity === 'high' ? 'destructive' : 'secondary'}>{t.severity}</Badge>
                </div>
                <div className="text-sm text-gray-600">{t.description}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>引擎统计</CardTitle></CardHeader>
        <CardContent>
          {!status || Object.keys(status.stats || {}).length === 0 ? (
            <div className="text-gray-500 text-center py-6">暂无统计数据</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(status.stats).map(([k, v]) => (
                <div key={k} className="border rounded p-3">
                  <div className="text-sm text-gray-600">{k}</div>
                  <div className="text-xl font-bold">{String(v)}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
