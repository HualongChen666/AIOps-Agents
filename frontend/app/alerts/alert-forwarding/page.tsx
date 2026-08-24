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
import { Share2, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface ForwardingRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  source_type: 'prometheus' | 'grafana' | 'datadog' | 'pagerduty' | 'cloudwatch' | 'zabbix';
  target_type: 'email' | 'slack' | 'webhook' | 'pagerduty' | 'teams';
  target_config: Record<string, any>;
  filter_conditions: Array<{
    field: string;
    operator: string;
    value: string;
  }>;
  transformation?: string;
  created_at: string;
  updated_at: string;
}

interface ForwardingLog {
  id: string;
  rule_id: string;
  rule_name: string;
  source_alert_id: string;
  target_type: string;
  status: 'success' | 'failed' | 'pending';
  error_message?: string;
  timestamp: string;
}

export default function AlertForwardingPage() {
  const [selectedRule, setSelectedRule] = useState<ForwardingRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'logs'>('rules');
  const [filters, setFilters] = useState({
    enabled: 'all',
    sourceType: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<ForwardingRule>>({
    name: '',
    description: '',
    enabled: true,
    source_type: 'prometheus',
    target_type: 'webhook',
    target_config: {},
    filter_conditions: [],
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: rulesData, isLoading: rulesLoading, error: rulesError, refetch: refetchRules } = useQuery<ForwardingRule[]>({
    queryKey: ['forwarding-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/forwarding/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery<ForwardingLog[]>({
    queryKey: ['forwarding-logs'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/forwarding/logs?limit=50');
      return resp.data.logs || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createRuleMutation = useMutation({
    mutationFn: async (data: Partial<ForwardingRule>) => {
      const resp = await api.post('/api/v1/alerts/forwarding/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('转发规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['forwarding-rules'] });
    },
    onError: () => showError('创建转发规则失败'),
  });

  const updateRuleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<ForwardingRule> }) => {
      const resp = await api.put(`/api/v1/alerts/forwarding/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('转发规则更新成功');
      setShowDialog(false);
      setSelectedRule(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['forwarding-rules'] });
    },
    onError: () => showError('更新转发规则失败'),
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/forwarding/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('转发规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['forwarding-rules'] });
    },
    onError: () => showError('删除转发规则失败'),
  });

  useEffect(() => {
    if (rulesError) showError('Failed to load forwarding rules');
  }, [rulesError, showError]);

  const filteredRules = (rulesData || []).filter((rule) => {
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !rule.enabled : rule.enabled)) return false;
    if (filters.sourceType !== 'all' && rule.source_type !== filters.sourceType) return false;
    if (debouncedSearch && !rule.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      description: '',
      enabled: true,
      source_type: 'prometheus',
      target_type: 'webhook',
      target_config: {},
      filter_conditions: [],
    });
    setShowDialog(true);
  };

  const handleEdit = (rule: ForwardingRule) => {
    setIsEditing(true);
    setSelectedRule(rule);
    setFormData(rule);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此转发规则吗？')) return;
    deleteRuleMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedRule) {
      updateRuleMutation.mutate({ id: selectedRule.id, data: formData });
    } else {
      createRuleMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (rule: ForwardingRule) => {
    updateRuleMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } });
  };

  const getSourceTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      prometheus: 'bg-orange-100 text-orange-800',
      grafana: 'bg-yellow-100 text-yellow-800',
      datadog: 'bg-purple-100 text-purple-800',
      pagerduty: 'bg-green-100 text-green-800',
      cloudwatch: 'bg-blue-100 text-blue-800',
      zabbix: 'bg-red-100 text-red-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getTargetTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      email: 'bg-blue-100 text-blue-800',
      slack: 'bg-purple-100 text-purple-800',
      webhook: 'bg-green-100 text-green-800',
      pagerduty: 'bg-red-100 text-red-800',
      teams: 'bg-cyan-100 text-cyan-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  if (rulesLoading || logsLoading) {
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
          <Share2 className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警转发</h1>
            <p className="text-sm text-gray-500">配置告警转发规则将告警发送到外部系统</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建转发规则
          </Button>
          <Button onClick={() => { refetchRules(); refetchLogs(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('rules')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'rules' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              转发规则
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'logs' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              转发日志 ({logsData?.length || 0})
            </button>
          </div>
        </CardContent>
      </Card>

      {activeTab === 'rules' && (
        <>
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">源类型</label>
                  <Select
                    value={filters.sourceType}
                    onChange={(e) => setFilters({ ...filters, sourceType: e.target.value })}
                  >
                    <option value="all">全部</option>
                    <option value="prometheus">Prometheus</option>
                    <option value="grafana">Grafana</option>
                    <option value="datadog">Datadog</option>
                    <option value="pagerduty">PagerDuty</option>
                    <option value="cloudwatch">CloudWatch</option>
                    <option value="zabbix">Zabbix</option>
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
              <CardTitle>转发规则 ({filteredRules.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>源类型</TableHead>
                    <TableHead>目标类型</TableHead>
                    <TableHead>过滤条件</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <EmptyState
                          title="没有转发规则"
                          description="当前没有转发规则"
                          action={<Button onClick={handleCreate}>创建第一个转发规则</Button>}
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
                        <TableCell>
                          <Badge className={getSourceTypeColor(rule.source_type)}>
                            {rule.source_type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getTargetTypeColor(rule.target_type)}>
                            {rule.target_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">{rule.filter_conditions.length} 条</TableCell>
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

      {activeTab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle>转发日志</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>规则名称</TableHead>
                  <TableHead>源告警ID</TableHead>
                  <TableHead>目标类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>错误信息</TableHead>
                  <TableHead>时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!logsData || logsData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <EmptyState title="没有日志" description="当前没有转发日志" />
                    </TableCell>
                  </TableRow>
                ) : (
                  logsData.map((log) => (
                    <TableRow key={log.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{log.rule_name}</TableCell>
                      <TableCell className="font-mono text-sm">{log.source_alert_id}</TableCell>
                      <TableCell className="text-sm">{log.target_type}</TableCell>
                      <TableCell>
                        <Badge className={log.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {log.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500 truncate max-w-xs">{log.error_message || '-'}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(log.timestamp).toLocaleString()}
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
            <DialogTitle>{isEditing ? '编辑转发规则' : '创建转发规则'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入转发规则名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入转发规则描述"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">源类型</label>
                <Select
                  value={formData.source_type}
                  onChange={(e) => setFormData({ ...formData, source_type: e.target.value as any })}
                >
                  <option value="prometheus">Prometheus</option>
                  <option value="grafana">Grafana</option>
                  <option value="datadog">Datadog</option>
                  <option value="pagerduty">PagerDuty</option>
                  <option value="cloudwatch">CloudWatch</option>
                  <option value="zabbix">Zabbix</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">目标类型</label>
                <Select
                  value={formData.target_type}
                  onChange={(e) => setFormData({ ...formData, target_type: e.target.value as any })}
                >
                  <option value="email">邮件</option>
                  <option value="slack">Slack</option>
                  <option value="webhook">Webhook</option>
                  <option value="pagerduty">PagerDuty</option>
                  <option value="teams">Teams</option>
                </Select>
              </div>
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
