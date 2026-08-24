'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Layers, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface AggregationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  group_by: string[];
  aggregation_type: 'sum' | 'avg' | 'count' | 'min' | 'max';
  window: number;
  threshold: number;
  match_conditions: Array<{
    field: string;
    operator: string;
    value: string;
  }>;
  created_at: string;
  updated_at: string;
}

interface AggregatedAlert {
  id: string;
  rule_id: string;
  rule_name: string;
  group_key: string;
  count: number;
  value: number;
  severity: string;
  first_seen: string;
  last_seen: string;
  status: string;
}

export default function AlertAggregationPage() {
  const [selectedRule, setSelectedRule] = useState<AggregationRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'alerts'>('rules');
  const [filters, setFilters] = useState({
    enabled: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<AggregationRule>>({
    name: '',
    description: '',
    enabled: true,
    group_by: [],
    aggregation_type: 'count',
    window: 300,
    threshold: 5,
    match_conditions: [],
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  // 获取聚合规则列表
  const { data: rulesData, isLoading: rulesLoading, error: rulesError, refetch: refetchRules } = useQuery<AggregationRule[]>({
    queryKey: ['aggregation-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/aggregation/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 30000,
  });

  // 获取聚合告警列表
  const { data: alertsData, isLoading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useQuery<AggregatedAlert[]>({
    queryKey: ['aggregated-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/aggregation/alerts');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createRuleMutation = useMutation({
    mutationFn: async (data: Partial<AggregationRule>) => {
      const resp = await api.post('/api/v1/alerts/aggregation/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['aggregation-rules'] });
    },
    onError: () => {
      showError('创建规则失败');
    },
  });

  const updateRuleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<AggregationRule> }) => {
      const resp = await api.put(`/api/v1/alerts/aggregation/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则更新成功');
      setShowDialog(false);
      setSelectedRule(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['aggregation-rules'] });
    },
    onError: () => {
      showError('更新规则失败');
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/aggregation/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['aggregation-rules'] });
    },
    onError: () => {
      showError('删除规则失败');
    },
  });

  useEffect(() => {
    if (rulesError) showError('Failed to load aggregation rules');
    if (alertsError) showError('Failed to load aggregated alerts');
  }, [rulesError, alertsError, showError]);

  const filteredRules = (rulesData || []).filter((rule) => {
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !rule.enabled : rule.enabled)) return false;
    if (debouncedSearch && !rule.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      description: '',
      enabled: true,
      group_by: [],
      aggregation_type: 'count',
      window: 300,
      threshold: 5,
      match_conditions: [],
    });
    setShowDialog(true);
  };

  const handleEdit = (rule: AggregationRule) => {
    setIsEditing(true);
    setSelectedRule(rule);
    setFormData(rule);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此规则吗？')) return;
    deleteRuleMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedRule) {
      updateRuleMutation.mutate({ id: selectedRule.id, data: formData });
    } else {
      createRuleMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (rule: AggregationRule) => {
    updateRuleMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } });
  };

  if (rulesLoading || alertsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layers className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警聚合</h1>
            <p className="text-sm text-gray-500">配置告警聚合规则和查看聚合结果</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建规则
          </Button>
          <Button onClick={() => { refetchRules(); refetchAlerts(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('rules')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'rules' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              聚合规则
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'alerts' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              聚合告警 ({alertsData?.length || 0})
            </button>
          </div>
        </CardContent>
      </Card>

      {activeTab === 'rules' && (
        <>
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Select
                    value={filters.enabled}
                    onChange={(e) => setFilters({ ...filters, enabled: e.target.value })}
                  >
                    <option value="all">全部</option>
                    <option value="enabled">已启用</option>
                    <option value="disabled">已禁用</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
                  <Input
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    placeholder="搜索规则名称"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>聚合规则 ({filteredRules.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>分组字段</TableHead>
                    <TableHead>聚合类型</TableHead>
                    <TableHead>时间窗口</TableHead>
                    <TableHead>阈值</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <EmptyState
                          title="没有规则"
                          description="当前没有符合条件的聚合规则"
                          action={<Button onClick={handleCreate}>创建第一个规则</Button>}
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredRules.map((rule) => (
                      <TableRow key={rule.id} className="cursor-pointer hover:bg-gray-50">
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell>
                          <Badge className={rule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {rule.enabled ? '已启用' : '已禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">{rule.group_by.join(', ')}</TableCell>
                        <TableCell className="text-sm">{rule.aggregation_type}</TableCell>
                        <TableCell className="text-sm">{rule.window}s</TableCell>
                        <TableCell className="font-mono text-sm">{rule.threshold}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleToggleEnabled(rule)}>
                              {rule.enabled ? '禁用' : '启用'}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(rule)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(rule.id)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle>聚合告警 ({alertsData?.length || 0})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>规则名称</TableHead>
                  <TableHead>分组键</TableHead>
                  <TableHead>数量</TableHead>
                  <TableHead>值</TableHead>
                  <TableHead>严重度</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>最后出现</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!alertsData || alertsData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <EmptyState title="没有聚合告警" description="当前没有聚合告警" />
                    </TableCell>
                  </TableRow>
                ) : (
                  alertsData.map((alert) => (
                    <TableRow key={alert.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{alert.rule_name}</TableCell>
                      <TableCell className="font-mono text-sm">{alert.group_key}</TableCell>
                      <TableCell className="font-mono text-sm">{alert.count}</TableCell>
                      <TableCell className="font-mono text-sm">{alert.value}</TableCell>
                      <TableCell>
                        <Badge className={alert.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}>
                          {alert.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={alert.status === 'active' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}>
                          {alert.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(alert.last_seen).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isEditing ? '编辑规则' : '创建规则'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入规则名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入规则描述"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">聚合类型</label>
                <Select
                  value={formData.aggregation_type}
                  onChange={(e) => setFormData({ ...formData, aggregation_type: e.target.value as any })}
                >
                  <option value="count">计数</option>
                  <option value="sum">求和</option>
                  <option value="avg">平均</option>
                  <option value="min">最小</option>
                  <option value="max">最大</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用</label>
                <Select
                  value={formData.enabled ? 'true' : 'false'}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">时间窗口(秒)</label>
                <Input
                  type="number"
                  value={formData.window}
                  onChange={(e) => setFormData({ ...formData, window: parseInt(e.target.value) || 300 })}
                  placeholder="300"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">阈值</label>
                <Input
                  type="number"
                  value={formData.threshold}
                  onChange={(e) => setFormData({ ...formData, threshold: parseInt(e.target.value) || 5 })}
                  placeholder="5"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分组字段(逗号分隔)</label>
              <Input
                value={formData.group_by?.join(',')}
                onChange={(e) => setFormData({ ...formData, group_by: e.target.value.split(',').map(s => s.trim()) })}
                placeholder="service,severity"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>取消</Button>
            <Button onClick={handleSave} disabled={createRuleMutation.isPending || updateRuleMutation.isPending}>
              {isEditing ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
