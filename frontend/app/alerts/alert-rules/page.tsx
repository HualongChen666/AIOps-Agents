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
import { List, Plus, Edit, Trash2, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface AlertRule {
  id: string;
  name: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  enabled: boolean;
  condition: string;
  threshold: number;
  operator: '>' | '<' | '=' | '>=' | '<=' | '!=';
  metric: string;
  labels: Record<string, string>;
  duration: number;
  notification_channels: string[];
  created_at: string;
  updated_at: string;
}

export default function AlertRulesPage() {
  const [selectedRule, setSelectedRule] = useState<AlertRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [filters, setFilters] = useState({
    severity: 'all',
    enabled: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<AlertRule>>({
    name: '',
    description: '',
    severity: 'medium',
    enabled: true,
    condition: '',
    threshold: 0,
    operator: '>',
    metric: '',
    labels: {},
    duration: 60,
    notification_channels: [],
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  // 获取告警规则列表
  const { data: rulesData, isLoading: rulesLoading, error: rulesError, refetch: refetchRules } = useQuery<AlertRule[]>({
    queryKey: ['alert-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 30000, // 30秒刷新
  });

  // 创建规则
  const createRuleMutation = useMutation({
    mutationFn: async (data: Partial<AlertRule>) => {
      const resp = await api.post('/api/v1/alerts/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    },
    onError: () => {
      showError('创建规则失败');
    },
  });

  // 更新规则
  const updateRuleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<AlertRule> }) => {
      const resp = await api.put(`/api/v1/alerts/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则更新成功');
      setShowDialog(false);
      setSelectedRule(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    },
    onError: () => {
      showError('更新规则失败');
    },
  });

  // 删除规则
  const deleteRuleMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    },
    onError: () => {
      showError('删除规则失败');
    },
  });

  useEffect(() => {
    if (rulesError) {
      showError('Failed to load alert rules');
    }
  }, [rulesError, showError]);

  const filteredRules = (rulesData || []).filter((rule) => {
    if (filters.severity !== 'all' && rule.severity !== filters.severity) return false;
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !rule.enabled : rule.enabled)) return false;
    if (debouncedSearch && !rule.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      description: '',
      severity: 'medium',
      enabled: true,
      condition: '',
      threshold: 0,
      operator: '>',
      metric: '',
      labels: {},
      duration: 60,
      notification_channels: [],
    });
    setShowDialog(true);
  };

  const handleEdit = (rule: AlertRule) => {
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

  const handleToggleEnabled = async (rule: AlertRule) => {
    updateRuleMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } });
  };

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

  if (rulesLoading) {
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
          <List className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警规则</h1>
            <p className="text-sm text-gray-500">管理和配置告警规则</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建规则
          </Button>
          <Button onClick={() => refetchRules()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">严重度</label>
              <Select
                value={filters.severity}
                onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="critical">严重</option>
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </Select>
            </div>
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

      {/* 规则列表 */}
      <Card>
        <CardHeader>
          <CardTitle>规则列表 ({filteredRules.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>严重度</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>指标</TableHead>
                <TableHead>条件</TableHead>
                <TableHead>阈值</TableHead>
                <TableHead>持续时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRules.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState
                      title="没有规则"
                      description="当前没有符合条件的告警规则"
                      action={<Button onClick={handleCreate}>创建第一个规则</Button>}
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredRules.map((rule) => (
                  <TableRow key={rule.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(rule.severity)}>
                        {rule.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={rule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {rule.enabled ? '已启用' : '已禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm font-mono">{rule.metric}</TableCell>
                    <TableCell className="text-sm">{rule.operator}</TableCell>
                    <TableCell className="font-mono text-sm">{rule.threshold}</TableCell>
                    <TableCell className="text-sm">{rule.duration}s</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleEnabled(rule)}
                        >
                          {rule.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(rule)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(rule.id)}
                        >
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

      {/* 创建/编辑对话框 */}
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
                <label className="block text-sm font-medium text-gray-700 mb-1">严重度</label>
                <Select
                  value={formData.severity}
                  onChange={(e) => setFormData({ ...formData, severity: e.target.value as any })}
                >
                  <option value="critical">严重</option>
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">指标</label>
              <Input
                value={formData.metric}
                onChange={(e) => setFormData({ ...formData, metric: e.target.value })}
                placeholder="例如: cpu_usage"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">操作符</label>
                <Select
                  value={formData.operator}
                  onChange={(e) => setFormData({ ...formData, operator: e.target.value as any })}
                >
                  <option value=">">&gt;</option>
                  <option value="<">&lt;</option>
                  <option value="=">=</option>
                  <option value=">=">&gt;=</option>
                  <option value="<=">&lt;=</option>
                  <option value="!=">!=</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">阈值</label>
                <Input
                  type="number"
                  value={formData.threshold}
                  onChange={(e) => setFormData({ ...formData, threshold: parseFloat(e.target.value) || 0 })}
                  placeholder="输入阈值"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">持续时间(秒)</label>
                <Input
                  type="number"
                  value={formData.duration}
                  onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) || 0 })}
                  placeholder="60"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">条件表达式</label>
              <Input
                value={formData.condition}
                onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
                placeholder="例如: avg_over_time(cpu_usage[5m])"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={createRuleMutation.isPending || updateRuleMutation.isPending}>
              {isEditing ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
