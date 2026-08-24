'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LogAlertRule {
  id?: string;
  name?: string;
  pattern?: string;
  severity?: string;
  status?: string;
  triggered_count?: number;
  last_triggered?: string;
  notification_channels?: string[];
  [key: string]: any;
}

interface LogAlertingData {
  total_rules?: number;
  active_rules?: number;
  inactive_rules?: number;
  total_alerts?: number;
  rules?: LogAlertRule[];
  [key: string]: any;
}

export default function LogAlertingPage() {
  const [selectedStatus, setSelectedStatus] = useState('all');

  const { data: alertingData, isLoading, error, refetch } = useQuery<LogAlertingData>({
    queryKey: ['monitoring-log-alerting', selectedStatus],
    queryFn: async () => {
      const params = selectedStatus !== 'all' ? { status: selectedStatus } : {};
      const resp = await api.get('/api/v1/monitoring/log-alerting', { params });
      return resp.data;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleRuleAction = async (ruleId: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/log-alerting/rule-action', {
        rule_id: ruleId,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform rule action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">日志告警</h1>
        <div className="flex gap-2">
          <Select value={selectedStatus} onChange={(e) => setSelectedStatus(e.target.value)}>
            <option value="all">所有状态</option>
            <option value="active">活跃</option>
            <option value="inactive">非活跃</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总规则数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{alertingData?.total_rules || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃规则</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{alertingData?.active_rules || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">非活跃规则</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{alertingData?.inactive_rules || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总告警数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{alertingData?.total_alerts?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>告警规则列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">规则名称</th>
                  <th className="px-4 py-2 text-left">匹配模式</th>
                  <th className="px-4 py-2 text-left">严重性</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">触发次数</th>
                  <th className="px-4 py-2 text-left">最后触发</th>
                  <th className="px-4 py-2 text-left">通知渠道</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {alertingData?.rules?.map((rule, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{rule.name}</td>
                    <td className="px-4 py-2 max-w-xs truncate">{rule.pattern}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        rule.severity === 'critical' ? 'bg-red-100 text-red-800' : 
                        rule.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {rule.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        rule.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {rule.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{rule.triggered_count?.toLocaleString()}</td>
                    <td className="px-4 py-2">
                      {rule.last_triggered ? new Date(rule.last_triggered).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {rule.notification_channels?.map((channel, j) => (
                          <span key={j} className="px-2 py-1 bg-gray-100 rounded text-xs">
                            {channel}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          onClick={() => rule.id && handleRuleAction(rule.id, rule.status === 'active' ? 'disable' : 'enable')}
                        >
                          {rule.status === 'active' ? '禁用' : '启用'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => rule.id && handleRuleAction(rule.id, 'test')}
                        >
                          测试
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
