'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface HAConfig {
  ha_enabled: boolean;
  ha_mode: string;
  nodes: number;
  load_balancer: string;
  health_check_interval_seconds: number;
  failover_timeout_seconds: number;
  auto_failover_enabled: boolean;
}

export default function HaConfigurationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<HAConfig | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/ha-configuration');
      setConfig(res.data.ha_configuration);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载高可用配置失败');
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

  if (error || !config) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error || '无高可用配置'}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  const rows: [string, React.ReactNode][] = [
    ['高可用', <Badge key="e" variant={config.ha_enabled ? 'default' : 'secondary'}>{config.ha_enabled ? '已启用' : '已停用'}</Badge>],
    ['模式', config.ha_mode],
    ['节点数', config.nodes],
    ['负载均衡器', config.load_balancer],
    ['健康检查间隔', `${config.health_check_interval_seconds} 秒`],
    ['故障转移超时', `${config.failover_timeout_seconds} 秒`],
    ['自动故障转移', <Badge key="a" variant={config.auto_failover_enabled ? 'default' : 'secondary'}>{config.auto_failover_enabled ? '开启' : '关闭'}</Badge>],
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高可用配置</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>配置详情</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <tbody>
              {rows.map(([k, v]) => (
                <tr key={k} className="border-b">
                  <td className="py-3 text-gray-600 w-1/3">{k}</td>
                  <td className="py-3">{v as any}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
