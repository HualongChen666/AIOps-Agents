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

interface Attribute {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'list';
  category: 'user' | 'resource' | 'environment' | 'action';
  description: string;
  values?: string[];
}

interface Policy {
  id: string;
  name: string;
  description: string;
  effect: 'allow' | 'deny';
  conditions: {
    attribute: string;
    operator: 'equals' | 'not_equals' | 'contains' | 'greater_than' | 'less_than' | 'in';
    value: string;
  }[];
  resources: string[];
  actions: string[];
  priority: number;
  enabled: boolean;
  createdAt: string;
}

interface AccessLog {
  id: string;
  timestamp: string;
  userId: string;
  resource: string;
  action: string;
  policyId: string;
  policyName: string;
  effect: 'allow' | 'deny';
  attributes: Record<string, any>;
  reason: string;
}

export default function AbacPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [activeTab, setActiveTab] = useState<'policies' | 'attributes' | 'logs'>('policies');
  const [showAddPolicyModal, setShowAddPolicyModal] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    name: '',
    description: '',
    effect: 'allow' as const,
    resources: [] as string[],
    actions: [] as string[],
    priority: 1,
  });

  const loadAbacData = async () => {
    setLoading(true);
    try {
      const [attributesRes, policiesRes, logsRes] = await Promise.all([
        api.get('/api/v1/security/abac/attributes'),
        api.get('/api/v1/security/abac/policies'),
        api.get('/api/v1/security/abac/logs'),
      ]);

      const attributesData = attributesRes.data?.attributes || [];
      const policiesData = policiesRes.data?.policies || [];
      const logsData = logsRes.data?.logs || [];

      setAttributes(attributesData);
      setPolicies(policiesData);
      setLogs(logsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddPolicy = async () => {
    try {
      await api.post('/api/v1/security/abac/policies', {
        ...newPolicy,
        conditions: [],
      });
      success('策略添加成功');
      setShowAddPolicyModal(false);
      setNewPolicy({
        name: '',
        description: '',
        effect: 'allow',
        resources: [],
        actions: [],
        priority: 1,
      });
      loadAbacData();
    } catch (err) {
      showError('策略添加失败');
    }
  };

  const handleTogglePolicy = async (policyId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/abac/policies/${policyId}`, { enabled });
      success('策略状态更新成功');
      loadAbacData();
    } catch (err) {
      showError('策略状态更新失败');
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    try {
      await api.delete(`/api/v1/security/abac/policies/${policyId}`);
      success('策略删除成功');
      loadAbacData();
    } catch (err) {
      showError('策略删除失败');
    }
  };

  useEffect(() => {
    loadAbacData();
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

  const getEffectColor = (effect: string) => {
    switch (effect) {
      case 'allow':
        return 'bg-green-100 text-green-800';
      case 'deny':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'user':
        return 'bg-blue-100 text-blue-800';
      case 'resource':
        return 'bg-purple-100 text-purple-800';
      case 'environment':
        return 'bg-yellow-100 text-yellow-800';
      case 'action':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'policies' as const, label: '访问策略' },
    { key: 'attributes' as const, label: '属性定义' },
    { key: 'logs' as const, label: '访问日志' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">属性访问控制 (ABAC)</h1>
        <div className="flex gap-2">
          <Button onClick={loadAbacData}>刷新数据</Button>
          <Button onClick={() => setShowAddPolicyModal(true)}>添加策略</Button>
        </div>
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

      {/* 访问策略 */}
      {activeTab === 'policies' && (
        <Card>
          <CardHeader>
            <CardTitle>访问策略</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>效果</TableHead>
                  <TableHead>资源</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>条件数</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.length > 0 ? policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell className="font-medium">{policy.name}</TableCell>
                    <TableCell>
                      <Badge className={getEffectColor(policy.effect)}>{policy.effect}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {policy.resources.slice(0, 2).map((res, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{res}</Badge>
                        ))}
                        {policy.resources.length > 2 && (
                          <Badge variant="outline" className="text-xs">+{policy.resources.length - 2}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {policy.actions.slice(0, 2).map((act, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{act}</Badge>
                        ))}
                        {policy.actions.length > 2 && (
                          <Badge variant="outline" className="text-xs">+{policy.actions.length - 2}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{policy.conditions.length}</TableCell>
                    <TableCell>{policy.priority}</TableCell>
                    <TableCell>
                      <Badge className={policy.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {policy.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleTogglePolicy(policy.id, !policy.enabled)}
                        >
                          {policy.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeletePolicy(policy.id)}
                        >
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No access policies found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 属性定义 */}
      {activeTab === 'attributes' && (
        <Card>
          <CardHeader>
            <CardTitle>属性定义</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>可选值</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {attributes.length > 0 ? attributes.map((attr) => (
                  <TableRow key={attr.id}>
                    <TableCell className="font-medium">{attr.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{attr.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getCategoryColor(attr.category)}>{attr.category}</Badge>
                    </TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{attr.description}</TableCell>
                    <TableCell>
                      {attr.values ? (
                        <div className="flex flex-wrap gap-1">
                          {attr.values.slice(0, 3).map((val, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs">{val}</Badge>
                          ))}
                          {attr.values.length > 3 && (
                            <Badge variant="outline" className="text-xs">+{attr.values.length - 3}</Badge>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500">
                      No attributes found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 访问日志 */}
      {activeTab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle>访问日志</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>资源</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>策略</TableHead>
                  <TableHead>效果</TableHead>
                  <TableHead>原因</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.length > 0 ? logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{log.userId}</TableCell>
                    <TableCell className="font-mono text-sm">{log.resource}</TableCell>
                    <TableCell>{log.action}</TableCell>
                    <TableCell>{log.policyName}</TableCell>
                    <TableCell>
                      <Badge className={getEffectColor(log.effect)}>{log.effect}</Badge>
                    </TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{log.reason}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No access logs found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 添加策略模态框 */}
      {showAddPolicyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加访问策略</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">策略名称</label>
                <Input
                  value={newPolicy.name}
                  onChange={(e) => setNewPolicy({ ...newPolicy, name: e.target.value })}
                  placeholder="输入策略名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">描述</label>
                <Input
                  value={newPolicy.description}
                  onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
                  placeholder="策略描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">效果</label>
                <Select
                  value={newPolicy.effect}
                  onChange={(e) => setNewPolicy({ ...newPolicy, effect: e.target.value as any })}
                >
                  <option value="allow">允许</option>
                  <option value="deny">拒绝</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">资源 (逗号分隔)</label>
                <Input
                  value={newPolicy.resources.join(',')}
                  onChange={(e) => setNewPolicy({ ...newPolicy, resources: e.target.value.split(',').filter(r => r.trim()) })}
                  placeholder="/api/v1/*"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">操作 (逗号分隔)</label>
                <Input
                  value={newPolicy.actions.join(',')}
                  onChange={(e) => setNewPolicy({ ...newPolicy, actions: e.target.value.split(',').filter(a => a.trim()) })}
                  placeholder="read,write,delete"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">优先级</label>
                <Input
                  type="number"
                  value={newPolicy.priority}
                  onChange={(e) => setNewPolicy({ ...newPolicy, priority: parseInt(e.target.value) })}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddPolicyModal(false)}>取消</Button>
                <Button onClick={handleAddPolicy}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
