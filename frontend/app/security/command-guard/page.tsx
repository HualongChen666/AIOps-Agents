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

interface CommandRule {
  id: string;
  command: string;
  pattern: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  action: 'block' | 'warn' | 'allow' | 'rewrite';
  description: string;
  category: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

interface CommandEvent {
  id: string;
  timestamp: string;
  userId: string;
  command: string;
  matchedRule: string;
  action: string;
  result: string;
  ipAddress: string;
}

export default function CommandGuardPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [rules, setRules] = useState<CommandRule[]>([]);
  const [events, setEvents] = useState<CommandEvent[]>([]);
  const [stats, setStats] = useState({
    totalRules: 0,
    activeRules: 0,
    blockedCommands: 0,
    warnedCommands: 0,
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRule, setNewRule] = useState({
    command: '',
    pattern: '',
    severity: 'high' as const,
    action: 'block' as const,
    description: '',
    category: 'system',
  });

  const loadCommandGuardData = async () => {
    setLoading(true);
    try {
      const [rulesRes, eventsRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/command-guard/rules'),
        api.get('/api/v1/security/command-guard/events'),
        api.get('/api/v1/security/command-guard/stats'),
      ]);

      const rulesData = rulesRes.data?.rules || [];
      const eventsData = eventsRes.data?.events || [];
      const statsData = statsRes.data || {};

      setRules(rulesData);
      setEvents(eventsData);
      setStats({
        totalRules: statsData.totalRules || rulesData.length,
        activeRules: statsData.activeRules || rulesData.filter((r: CommandRule) => r.enabled).length,
        blockedCommands: statsData.blockedCommands || 0,
        warnedCommands: statsData.warnedCommands || 0,
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddRule = async () => {
    try {
      await api.post('/api/v1/security/command-guard/rules', newRule);
      success('规则添加成功');
      setShowAddModal(false);
      setNewRule({
        command: '',
        pattern: '',
        severity: 'high',
        action: 'block',
        description: '',
        category: 'system',
      });
      loadCommandGuardData();
    } catch (err) {
      showError('规则添加失败');
    }
  };

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/command-guard/rules/${ruleId}`, { enabled });
      success('规则状态更新成功');
      loadCommandGuardData();
    } catch (err) {
      showError('规则状态更新失败');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    try {
      await api.delete(`/api/v1/security/command-guard/rules/${ruleId}`);
      success('规则删除成功');
      loadCommandGuardData();
    } catch (err) {
      showError('规则删除失败');
    }
  };

  useEffect(() => {
    loadCommandGuardData();
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

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'block':
        return 'bg-red-100 text-red-800';
      case 'warn':
        return 'bg-yellow-100 text-yellow-800';
      case 'allow':
        return 'bg-green-100 text-green-800';
      case 'rewrite':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高危指令管控</h1>
        <div className="flex gap-2">
          <Button onClick={loadCommandGuardData}>刷新数据</Button>
          <Button onClick={() => setShowAddModal(true)}>添加规则</Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总规则数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{stats.totalRules}</p>
            <p className="text-sm text-gray-500">已配置规则</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">启用规则</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.activeRules}</p>
            <p className="text-sm text-gray-500">活跃规则</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">拦截命令</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{stats.blockedCommands}</p>
            <p className="text-sm text-gray-500">已拦截</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告命令</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{stats.warnedCommands}</p>
            <p className="text-sm text-gray-500">已警告</p>
          </CardContent>
        </Card>
      </div>

      {/* 规则列表 */}
      <Card>
        <CardHeader>
          <CardTitle>管控规则</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>命令</TableHead>
                <TableHead>模式</TableHead>
                <TableHead>严重性</TableHead>
                <TableHead>动作</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.length > 0 ? rules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell className="font-mono text-sm">{rule.command}</TableCell>
                  <TableCell className="font-mono text-sm">{rule.pattern}</TableCell>
                  <TableCell>
                    <Badge className={getSeverityColor(rule.severity)}>{rule.severity}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getActionColor(rule.action)}>{rule.action}</Badge>
                  </TableCell>
                  <TableCell>{rule.category}</TableCell>
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
                  <TableCell colSpan={7} className="text-center text-gray-500">
                    No rules found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 命令事件 */}
      <Card>
        <CardHeader>
          <CardTitle>命令执行事件</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>用户</TableHead>
                <TableHead>命令</TableHead>
                <TableHead>匹配规则</TableHead>
                <TableHead>动作</TableHead>
                <TableHead>结果</TableHead>
                <TableHead>IP地址</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.length > 0 ? events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{event.userId}</TableCell>
                  <TableCell className="font-mono text-sm">{event.command}</TableCell>
                  <TableCell>{event.matchedRule}</TableCell>
                  <TableCell>
                    <Badge className={getActionColor(event.action)}>{event.action}</Badge>
                  </TableCell>
                  <TableCell>{event.result}</TableCell>
                  <TableCell className="font-mono text-sm">{event.ipAddress}</TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-gray-500">
                    No command events found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 添加规则模态框 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <CardTitle>添加管控规则</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">命令</label>
                <Input
                  value={newRule.command}
                  onChange={(e) => setNewRule({ ...newRule, command: e.target.value })}
                  placeholder="例如: rm -rf"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">匹配模式</label>
                <Input
                  value={newRule.pattern}
                  onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
                  placeholder="正则表达式"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">严重性</label>
                <Select
                  value={newRule.severity}
                  onChange={(e) => setNewRule({ ...newRule, severity: e.target.value as any })}
                >
                  <option value="critical">严重</option>
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">动作</label>
                <Select
                  value={newRule.action}
                  onChange={(e) => setNewRule({ ...newRule, action: e.target.value as any })}
                >
                  <option value="block">拦截</option>
                  <option value="warn">警告</option>
                  <option value="allow">允许</option>
                  <option value="rewrite">重写</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">分类</label>
                <Input
                  value={newRule.category}
                  onChange={(e) => setNewRule({ ...newRule, category: e.target.value })}
                  placeholder="例如: system, network, database"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">描述</label>
                <Input
                  value={newRule.description}
                  onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                  placeholder="规则描述"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddModal(false)}>取消</Button>
                <Button onClick={handleAddRule}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
