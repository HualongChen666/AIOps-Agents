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

interface RewriteRule {
  id: string;
  name: string;
  originalPattern: string;
  rewrittenCommand: string;
  description: string;
  category: string;
  enabled: boolean;
  priority: number;
  createdAt: string;
}

interface RewriteHistory {
  id: string;
  originalCommand: string;
  rewrittenCommand: string;
  ruleId: string;
  ruleName: string;
  userId: string;
  timestamp: string;
}

export default function CommandRewritePage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [rules, setRules] = useState<RewriteRule[]>([]);
  const [history, setHistory] = useState<RewriteHistory[]>([]);
  const [stats, setStats] = useState({
    totalRules: 0,
    activeRules: 0,
    totalRewrites: 0,
    todayRewrites: 0,
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    originalPattern: '',
    rewrittenCommand: '',
    description: '',
    category: 'system',
    priority: 1,
  });
  const [testCommand, setTestCommand] = useState('');
  const [testResult, setTestResult] = useState<any>(null);

  const loadRewriteData = async () => {
    setLoading(true);
    try {
      const [rulesRes, historyRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/command-rewrite/rules'),
        api.get('/api/v1/security/command-rewrite/history'),
        api.get('/api/v1/security/command-rewrite/stats'),
      ]);

      const rulesData = rulesRes.data?.rules || [];
      const historyData = historyRes.data?.history || [];
      const statsData = statsRes.data || {};

      setRules(rulesData);
      setHistory(historyData);
      setStats({
        totalRules: statsData.totalRules || rulesData.length,
        activeRules: statsData.activeRules || rulesData.filter((r: RewriteRule) => r.enabled).length,
        totalRewrites: statsData.totalRewrites || 0,
        todayRewrites: statsData.todayRewrites || 0,
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddRule = async () => {
    try {
      await api.post('/api/v1/security/command-rewrite/rules', newRule);
      success('重写规则添加成功');
      setShowAddModal(false);
      setNewRule({
        name: '',
        originalPattern: '',
        rewrittenCommand: '',
        description: '',
        category: 'system',
        priority: 1,
      });
      loadRewriteData();
    } catch (err) {
      showError('规则添加失败');
    }
  };

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/command-rewrite/rules/${ruleId}`, { enabled });
      success('规则状态更新成功');
      loadRewriteData();
    } catch (err) {
      showError('规则状态更新失败');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    try {
      await api.delete(`/api/v1/security/command-rewrite/rules/${ruleId}`);
      success('规则删除成功');
      loadRewriteData();
    } catch (err) {
      showError('规则删除失败');
    }
  };

  const handleTestRewrite = async () => {
    if (!testCommand.trim()) {
      showError('请输入测试命令');
      return;
    }

    try {
      const response = await api.post('/api/v1/security/command-rewrite/test', {
        command: testCommand,
      });
      setTestResult(response.data);
      success('测试完成');
    } catch (err) {
      showError('测试失败');
    }
  };

  useEffect(() => {
    loadRewriteData();
  }, []);

  if (isLoading && !testResult) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error && !testResult) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">命令重写</h1>
        <div className="flex gap-2">
          <Button onClick={loadRewriteData}>刷新数据</Button>
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
            <CardTitle className="text-sm">总重写次数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{stats.totalRewrites}</p>
            <p className="text-sm text-gray-500">历史累计</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">今日重写</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{stats.todayRewrites}</p>
            <p className="text-sm text-gray-500">今日执行</p>
          </CardContent>
        </Card>
      </div>

      {/* 命令重写测试 */}
      <Card>
        <CardHeader>
          <CardTitle>命令重写测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={testCommand}
                onChange={(e) => setTestCommand(e.target.value)}
                placeholder="输入要测试的命令"
                className="flex-1 font-mono"
                onKeyPress={(e) => e.key === 'Enter' && handleTestRewrite()}
              />
              <Button onClick={handleTestRewrite}>测试</Button>
              <Button variant="outline" onClick={() => { setTestCommand(''); setTestResult(null); }}>
                清除
              </Button>
            </div>

            {testResult && (
              <div className="space-y-3">
                <div className="p-4 border rounded-lg">
                  <h4 className="font-semibold mb-2">原始命令</h4>
                  <div className="font-mono text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded">
                    {testResult.originalCommand}
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <h4 className="font-semibold mb-2">重写后命令</h4>
                  <div className="font-mono text-sm bg-green-50 dark:bg-green-900/20 p-3 rounded">
                    {testResult.rewrittenCommand}
                  </div>
                </div>
                {testResult.matchedRule && (
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-semibold mb-2">匹配规则</h4>
                    <p className="text-sm">{testResult.matchedRule}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 重写规则列表 */}
      <Card>
        <CardHeader>
          <CardTitle>重写规则</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>原始模式</TableHead>
                <TableHead>重写命令</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.length > 0 ? rules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell className="font-medium">{rule.name}</TableCell>
                  <TableCell className="font-mono text-sm">{rule.originalPattern}</TableCell>
                  <TableCell className="font-mono text-sm">{rule.rewrittenCommand}</TableCell>
                  <TableCell>{rule.category}</TableCell>
                  <TableCell>{rule.priority}</TableCell>
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
                    No rewrite rules found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 重写历史 */}
      <Card>
        <CardHeader>
          <CardTitle>重写历史</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>原始命令</TableHead>
                <TableHead>重写命令</TableHead>
                <TableHead>规则</TableHead>
                <TableHead>用户</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.length > 0 ? history.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{new Date(item.timestamp).toLocaleString()}</TableCell>
                  <TableCell className="font-mono text-sm">{item.originalCommand}</TableCell>
                  <TableCell className="font-mono text-sm">{item.rewrittenCommand}</TableCell>
                  <TableCell>{item.ruleName}</TableCell>
                  <TableCell>{item.userId}</TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-gray-500">
                    No rewrite history found
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
              <CardTitle>添加重写规则</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">规则名称</label>
                <Input
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  placeholder="例如: 安全删除命令"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">原始模式</label>
                <Input
                  value={newRule.originalPattern}
                  onChange={(e) => setNewRule({ ...newRule, originalPattern: e.target.value })}
                  placeholder="正则表达式匹配原始命令"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">重写命令</label>
                <Input
                  value={newRule.rewrittenCommand}
                  onChange={(e) => setNewRule({ ...newRule, rewrittenCommand: e.target.value })}
                  placeholder="重写后的安全命令"
                />
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
                <label className="block text-sm font-medium mb-1">优先级</label>
                <Input
                  type="number"
                  value={newRule.priority}
                  onChange={(e) => setNewRule({ ...newRule, priority: parseInt(e.target.value) })}
                  placeholder="数字越大优先级越高"
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
