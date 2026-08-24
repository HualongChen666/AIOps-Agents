'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface RateLimitRule {
  id: string;
  name: string;
  endpoint: string;
  method: string;
  limit: number;
  window: number;
  windowUnit: 'second' | 'minute' | 'hour' | 'day';
  strategy: 'fixed' | 'sliding' | 'token_bucket';
  burst: number;
  enabled: boolean;
  createdAt: string;
}

interface RateLimitEvent {
  id: string;
  timestamp: string;
  ruleId: string;
  ruleName: string;
  endpoint: string;
  method: string;
  clientId: string;
  ipAddress: string;
  action: 'allowed' | 'blocked' | 'throttled';
  remaining: number;
  resetTime: string;
}

interface RateLimitStats {
  totalRequests: number;
  blockedRequests: number;
  throttledRequests: number;
  allowedRequests: number;
  topEndpoints: { endpoint: string; count: number }[];
  topClients: { clientId: string; count: number }[];
}

export default function RateLimitPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [rules, setRules] = useState<RateLimitRule[]>([]);
  const [events, setEvents] = useState<RateLimitEvent[]>([]);
  const [stats, setStats] = useState<RateLimitStats>({
    totalRequests: 0,
    blockedRequests: 0,
    throttledRequests: 0,
    allowedRequests: 0,
    topEndpoints: [],
    topClients: [],
  });
  const [activeTab, setActiveTab] = useState<'rules' | 'events' | 'stats'>('rules');
  const [showAddRuleModal, setShowAddRuleModal] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    endpoint: '',
    method: 'ALL',
    limit: 100,
    window: 1,
    windowUnit: 'minute' as const,
    strategy: 'fixed' as const,
    burst: 10,
  });

  const loadRateLimitData = async () => {
    setLoading(true);
    try {
      const [rulesRes, eventsRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/rate-limit/rules'),
        api.get('/api/v1/security/rate-limit/events'),
        api.get('/api/v1/security/rate-limit/stats'),
      ]);

      const rulesData = rulesRes.data?.rules || [];
      const eventsData = eventsRes.data?.events || [];
      const statsData = statsRes.data || {};

      setRules(rulesData);
      setEvents(eventsData);
      setStats({
        totalRequests: statsData.totalRequests || 0,
        blockedRequests: statsData.blockedRequests || 0,
        throttledRequests: statsData.throttledRequests || 0,
        allowedRequests: statsData.allowedRequests || 0,
        topEndpoints: statsData.topEndpoints || [],
        topClients: statsData.topClients || [],
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddRule = async () => {
    try {
      await api.post('/api/v1/security/rate-limit/rules', newRule);
      success('速率限制规则添加成功');
      setShowAddRuleModal(false);
      setNewRule({
        name: '',
        endpoint: '',
        method: 'ALL',
        limit: 100,
        window: 1,
        windowUnit: 'minute',
        strategy: 'fixed',
        burst: 10,
      });
      loadRateLimitData();
    } catch (err) {
      showError('规则添加失败');
    }
  };

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/rate-limit/rules/${ruleId}`, { enabled });
      success('规则状态更新成功');
      loadRateLimitData();
    } catch (err) {
      showError('规则状态更新失败');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    try {
      await api.delete(`/api/v1/security/rate-limit/rules/${ruleId}`);
      success('规则删除成功');
      loadRateLimitData();
    } catch (err) {
      showError('规则删除失败');
    }
  };

  useEffect(() => {
    loadRateLimitData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'allowed':
        return 'bg-green-100 text-green-800';
      case 'blocked':
        return 'bg-red-100 text-red-800';
      case 'throttled':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'rules' as const, label: '限制规则' },
    { key: 'events' as const, label: '限制事件' },
    { key: 'stats' as const, label: '统计信息' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">速率限制</h1>
        <div className="flex gap-2">
          <Button onClick={loadRateLimitData}>刷新数据</Button>
          <Button onClick={() => setShowAddRuleModal(true)}>添加规则</Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{stats.totalRequests}</p>
            <p className="text-sm text-gray-500">所有请求</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">允许请求</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.allowedRequests}</p>
            <p className="text-sm text-gray-500">通过限制</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">阻止请求</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{stats.blockedRequests}</p>
            <p className="text-sm text-gray-500">被阻止</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">限流请求</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{stats.throttledRequests}</p>
            <p className="text-sm text-gray-500">被限流</p>
          </CardContent>
        </Card>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 限制规则 */}
      {activeTab === 'rules' && (
        <Card>
          <CardHeader>
            <CardTitle>速率限制规则</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>端点</TableHead>
                  <TableHead>方法</TableHead>
                  <TableHead>限制</TableHead>
                  <TableHead>时间窗口</TableHead>
                  <TableHead>策略</TableHead>
                  <TableHead>突发</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.length > 0 ? rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell className="font-mono text-sm">{rule.endpoint}</TableCell>
                    <TableCell>{rule.method}</TableCell>
                    <TableCell>{rule.limit} 请求</TableCell>
                    <TableCell>{rule.window} {rule.windowUnit}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{rule.strategy}</Badge>
                    </TableCell>
                    <TableCell>{rule.burst}</TableCell>
                    <TableCell>
                      <Badge className={rule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {rule.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleRule(rule.id, !rule.enabled)}
                        >
                          {rule.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteRule(rule.id)}
                        >
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-gray-500">
                      No rate limit rules found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 限制事件 */}
      {activeTab === 'events' && (
        <Card>
          <CardHeader>
            <CardTitle>速率限制事件</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>规则</TableHead>
                  <TableHead>端点</TableHead>
                  <TableHead>方法</TableHead>
                  <TableHead>客户端ID</TableHead>
                  <TableHead>IP地址</TableHead>
                  <TableHead>动作</TableHead>
                  <TableHead>剩余</TableHead>
                  <TableHead>重置时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.length > 0 ? events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{event.ruleName}</TableCell>
                    <TableCell className="font-mono text-sm">{event.endpoint}</TableCell>
                    <TableCell>{event.method}</TableCell>
                    <TableCell>{event.clientId}</TableCell>
                    <TableCell className="font-mono text-sm">{event.ipAddress}</TableCell>
                    <TableCell>
                      <Badge className={getActionColor(event.action)}>{event.action}</Badge>
                    </TableCell>
                    <TableCell>{event.remaining}</TableCell>
                    <TableCell>{new Date(event.resetTime).toLocaleString()}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-gray-500">
                      No rate limit events found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 统计信息 */}
      {activeTab === 'stats' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>热门端点</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {stats.topEndpoints.length > 0 ? stats.topEndpoints.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="font-mono text-sm">{item.endpoint}</span>
                    <Badge>{item.count} 次请求</Badge>
                  </div>
                )) : (
                  <p className="text-center text-gray-500 py-4">暂无数据</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>活跃客户端</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {stats.topClients.length > 0 ? stats.topClients.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="font-mono text-sm">{item.clientId}</span>
                    <Badge>{item.count} 次请求</Badge>
                  </div>
                )) : (
                  <p className="text-center text-gray-500 py-4">暂无数据</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 添加规则模态框 */}
      {showAddRuleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加速率限制规则</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">规则名称</label>
                <Input
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  placeholder="输入规则名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">端点</label>
                <Input
                  value={newRule.endpoint}
                  onChange={(e) => setNewRule({ ...newRule, endpoint: e.target.value })}
                  placeholder="/api/v1/*"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">方法</label>
                <Select
                  value={newRule.method}
                  onChange={(e) => setNewRule({ ...newRule, method: e.target.value })}
                >
                  <option value="ALL">ALL</option>
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">限制数量</label>
                  <Input
                    type="number"
                    value={newRule.limit}
                    onChange={(e) => setNewRule({ ...newRule, limit: parseInt(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">时间窗口</label>
                  <Input
                    type="number"
                    value={newRule.window}
                    onChange={(e) => setNewRule({ ...newRule, window: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">时间单位</label>
                <Select
                  value={newRule.windowUnit}
                  onChange={(e) => setNewRule({ ...newRule, windowUnit: e.target.value as any })}
                >
                  <option value="second">秒</option>
                  <option value="minute">分钟</option>
                  <option value="hour">小时</option>
                  <option value="day">天</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">策略</label>
                <Select
                  value={newRule.strategy}
                  onChange={(e) => setNewRule({ ...newRule, strategy: e.target.value as any })}
                >
                  <option value="fixed">固定窗口</option>
                  <option value="sliding">滑动窗口</option>
                  <option value="token_bucket">令牌桶</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">突发容量</label>
                <Input
                  type="number"
                  value={newRule.burst}
                  onChange={(e) => setNewRule({ ...newRule, burst: parseInt(e.target.value) })}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddRuleModal(false)}>取消</Button>
                <Button onClick={handleAddRule}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
