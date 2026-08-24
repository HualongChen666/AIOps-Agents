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

interface ValidationRule {
  id: string;
  name: string;
  field: string;
  type: 'string' | 'number' | 'email' | 'url' | 'date' | 'json' | 'regex';
  pattern?: string;
  minLength?: number;
  maxLength?: number;
  minValue?: number;
  maxValue?: number;
  required: boolean;
  sanitize: boolean;
  enabled: boolean;
  createdAt: string;
}

interface ValidationEvent {
  id: string;
  timestamp: string;
  endpoint: string;
  field: string;
  value: string;
  ruleId: string;
  ruleName: string;
  result: 'passed' | 'failed' | 'sanitized';
  sanitizedValue?: string;
  userId: string;
  ipAddress: string;
}

interface ValidationStats {
  totalValidations: number;
  passedCount: number;
  failedCount: number;
  sanitizedCount: number;
  activeRules: number;
}

export default function InputValidationPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [events, setEvents] = useState<ValidationEvent[]>([]);
  const [stats, setStats] = useState<ValidationStats>({
    totalValidations: 0,
    passedCount: 0,
    failedCount: 0,
    sanitizedCount: 0,
    activeRules: 0,
  });
  const [showAddRuleModal, setShowAddRuleModal] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    field: '',
    type: 'string' as const,
    pattern: '',
    minLength: 0,
    maxLength: 1000,
    required: false,
    sanitize: false,
  });
  const [testInput, setTestInput] = useState('');
  const [testField, setTestField] = useState('');
  const [testResult, setTestResult] = useState<any>(null);

  const loadValidationData = async () => {
    setLoading(true);
    try {
      const [rulesRes, eventsRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/input-validation/rules'),
        api.get('/api/v1/security/input-validation/events'),
        api.get('/api/v1/security/input-validation/stats'),
      ]);

      const rulesData = rulesRes.data?.rules || [];
      const eventsData = eventsRes.data?.events || [];
      const statsData = statsRes.data || {};

      setRules(rulesData);
      setEvents(eventsData);
      setStats({
        totalValidations: statsData.totalValidations || eventsData.length,
        passedCount: statsData.passedCount || eventsData.filter((e: ValidationEvent) => e.result === 'passed').length,
        failedCount: statsData.failedCount || eventsData.filter((e: ValidationEvent) => e.result === 'failed').length,
        sanitizedCount: statsData.sanitizedCount || eventsData.filter((e: ValidationEvent) => e.result === 'sanitized').length,
        activeRules: statsData.activeRules || rulesData.filter((r: ValidationRule) => r.enabled).length,
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddRule = async () => {
    try {
      await api.post('/api/v1/security/input-validation/rules', newRule);
      success('验证规则添加成功');
      setShowAddRuleModal(false);
      setNewRule({
        name: '',
        field: '',
        type: 'string',
        pattern: '',
        minLength: 0,
        maxLength: 1000,
        required: false,
        sanitize: false,
      });
      loadValidationData();
    } catch (err) {
      showError('规则添加失败');
    }
  };

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/input-validation/rules/${ruleId}`, { enabled });
      success('规则状态更新成功');
      loadValidationData();
    } catch (err) {
      showError('规则状态更新失败');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    try {
      await api.delete(`/api/v1/security/input-validation/rules/${ruleId}`);
      success('规则删除成功');
      loadValidationData();
    } catch (err) {
      showError('规则删除失败');
    }
  };

  const handleTestValidation = async () => {
    if (!testField.trim() || !testInput.trim()) {
      showError('请输入字段名和测试值');
      return;
    }

    try {
      const response = await api.post('/api/v1/security/input-validation/test', {
        field: testField,
        value: testInput,
      });
      setTestResult(response.data);
      success('验证测试完成');
    } catch (err) {
      showError('验证测试失败');
    }
  };

  useEffect(() => {
    loadValidationData();
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

  const getResultColor = (result: string) => {
    switch (result) {
      case 'passed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'sanitized':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">输入验证</h1>
        <div className="flex gap-2">
          <Button onClick={loadValidationData}>刷新数据</Button>
          <Button onClick={() => setShowAddRuleModal(true)}>添加规则</Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总验证次数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{stats.totalValidations}</p>
            <p className="text-sm text-gray-500">输入验证</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">通过验证</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.passedCount}</p>
            <p className="text-sm text-gray-500">验证通过</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">验证失败</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{stats.failedCount}</p>
            <p className="text-sm text-gray-500">验证失败</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已清理</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{stats.sanitizedCount}</p>
            <p className="text-sm text-gray-500">输入清理</p>
          </CardContent>
        </Card>
      </div>

      {/* 验证测试 */}
      <Card>
        <CardHeader>
          <CardTitle>验证测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input
                placeholder="字段名"
                value={testField}
                onChange={(e) => setTestField(e.target.value)}
              />
              <Input
                placeholder="测试值"
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleTestValidation}>测试验证</Button>
              <Button variant="outline" onClick={() => { setTestField(''); setTestInput(''); setTestResult(null); }}>
                清除
              </Button>
            </div>

            {testResult && (
              <div className="space-y-3">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">验证结果</h4>
                    <Badge className={getResultColor(testResult.result)}>{testResult.result}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">原始值: </span>
                      <span className="font-mono">{testResult.originalValue}</span>
                    </div>
                    {testResult.sanitizedValue && (
                      <div>
                        <span className="text-gray-500">清理后: </span>
                        <span className="font-mono">{testResult.sanitizedValue}</span>
                      </div>
                    )}
                  </div>
                </div>
                {testResult.errors && testResult.errors.length > 0 && (
                  <div className="p-4 border border-red-200 bg-red-50 dark:bg-red-900/20 rounded-lg">
                    <h4 className="font-semibold text-red-800 dark:text-red-200 mb-2">验证错误</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {testResult.errors.map((error: string, idx: number) => (
                        <li key={idx} className="text-sm text-red-700 dark:text-red-300">{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 验证规则 */}
      <Card>
        <CardHeader>
          <CardTitle>验证规则</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>字段</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>必需</TableHead>
                <TableHead>清理</TableHead>
                <TableHead>限制</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.length > 0 ? rules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell className="font-medium">{rule.name}</TableCell>
                  <TableCell className="font-mono text-sm">{rule.field}</TableCell>
                  <TableCell>{rule.type}</TableCell>
                  <TableCell>
                    <Badge className={rule.required ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}>
                      {rule.required ? '是' : '否'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={rule.sanitize ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}>
                      {rule.sanitize ? '是' : '否'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {rule.minLength !== undefined && `最小: ${rule.minLength}`}
                    {rule.maxLength !== undefined && ` 最大: ${rule.maxLength}`}
                  </TableCell>
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
                  <TableCell colSpan={8} className="text-center text-gray-500">
                    No validation rules found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 验证事件 */}
      <Card>
        <CardHeader>
          <CardTitle>验证事件</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>端点</TableHead>
                <TableHead>字段</TableHead>
                <TableHead>值</TableHead>
                <TableHead>规则</TableHead>
                <TableHead>结果</TableHead>
                <TableHead>用户</TableHead>
                <TableHead>IP地址</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.length > 0 ? events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                  <TableCell className="font-mono text-sm">{event.endpoint}</TableCell>
                  <TableCell className="font-mono text-sm">{event.field}</TableCell>
                  <TableCell className="font-mono text-sm max-w-xs truncate">{event.value}</TableCell>
                  <TableCell>{event.ruleName}</TableCell>
                  <TableCell>
                    <Badge className={getResultColor(event.result)}>{event.result}</Badge>
                  </TableCell>
                  <TableCell>{event.userId}</TableCell>
                  <TableCell className="font-mono text-sm">{event.ipAddress}</TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-gray-500">
                    No validation events found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 添加规则模态框 */}
      {showAddRuleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加验证规则</CardTitle>
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
                <label className="block text-sm font-medium mb-1">字段名</label>
                <Input
                  value={newRule.field}
                  onChange={(e) => setNewRule({ ...newRule, field: e.target.value })}
                  placeholder="例如: username, email"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">类型</label>
                <Select
                  value={newRule.type}
                  onChange={(e) => setNewRule({ ...newRule, type: e.target.value as any })}
                >
                  <option value="string">字符串</option>
                  <option value="number">数字</option>
                  <option value="email">邮箱</option>
                  <option value="url">URL</option>
                  <option value="date">日期</option>
                  <option value="json">JSON</option>
                  <option value="regex">正则表达式</option>
                </Select>
              </div>
              {newRule.type === 'regex' && (
                <div>
                  <label className="block text-sm font-medium mb-1">正则模式</label>
                  <Input
                    value={newRule.pattern}
                    onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
                    placeholder="输入正则表达式"
                  />
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">最小长度</label>
                  <Input
                    type="number"
                    value={newRule.minLength}
                    onChange={(e) => setNewRule({ ...newRule, minLength: parseInt(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">最大长度</label>
                  <Input
                    type="number"
                    value={newRule.maxLength}
                    onChange={(e) => setNewRule({ ...newRule, maxLength: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newRule.required}
                    onChange={(e) => setNewRule({ ...newRule, required: e.target.checked })}
                  />
                  <span className="text-sm">必需字段</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newRule.sanitize}
                    onChange={(e) => setNewRule({ ...newRule, sanitize: e.target.checked })}
                  />
                  <span className="text-sm">自动清理</span>
                </label>
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
