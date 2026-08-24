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
import { Ban, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface SuppressionRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  match_conditions: Array<{
    field: string;
    operator: string;
    value: string;
  }>;
  duration?: number;
  start_time?: string;
  end_time?: string;
  reason: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface SuppressedAlert {
  id: string;
  alert_id: string;
  alert_title: string;
  rule_id: string;
  rule_name: string;
  suppressed_at: string;
  reason: string;
  expires_at?: string;
}

export default function AlertSuppressionPage() {
  const [selectedRule, setSelectedRule] = useState<SuppressionRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'alerts'>('rules');
  const [filters, setFilters] = useState({
    enabled: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<SuppressionRule>>({
    name: '',
    description: '',
    enabled: true,
    match_conditions: [],
    duration: 3600,
    reason: '',
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: rulesData, isLoading: rulesLoading, error: rulesError, refetch: refetchRules } = useQuery<SuppressionRule[]>({
    queryKey: ['suppression-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/suppression/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: alertsData, isLoading: alertsLoading, refetch: refetchAlerts } = useQuery<SuppressedAlert[]>({
    queryKey: ['suppressed-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/suppression/alerts');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createRuleMutation = useMutation({
    mutationFn: async (data: Partial<SuppressionRule>) => {
      const resp = await api.post('/api/v1/alerts/suppression/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('抑制规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['suppression-rules'] });
    },
    onError: () => showError('创建抑制规则失败'),
  });

  const updateRuleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<SuppressionRule> }) => {
      const resp = await api.put(`/api/v1/alerts/suppression/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('抑制规则更新成功');
      setShowDialog(false);
      setSelectedRule(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['suppression-rules'] });
    },
    onError: () => showError('更新抑制规则失败'),
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/suppression/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('抑制规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['suppression-rules'] });
    },
    onError: () => showError('删除抑制规则失败'),
  });

  useEffect(() => {
    if (rulesError) showError('Failed to load suppression rules');
  }, [rulesError, showError]);

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
      match_conditions: [],
      duration: 3600,
      reason: '',
    });
    setShowDialog(true);
  };

  const handleEdit = (rule: SuppressionRule) => {
    setIsEditing(true);
    setSelectedRule(rule);
    setFormData(rule);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此抑制规则吗？')) return;
    deleteRuleMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedRule) {
      updateRuleMutation.mutate({ id: selectedRule.id, data: formData });
    } else {
      createRuleMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (rule: SuppressionRule) => {
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
          <Ban className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警抑制</h1>
            <p className="text-sm text-gray-500">配置告警抑制规则以减少告警噪音</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建抑制规则
          </Button>
          <Button onClick={() => { refetchRules(); refetchAlerts(); }} variant="outline">
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
              抑制规则
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'alerts' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              被抑制告警 ({alertsData?.length || 0})
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
              <CardTitle>抑制规则 ({filteredRules.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>匹配条件</TableHead>
                    <TableHead>持续时间</TableHead>
                    <TableHead>原因</TableHead>
                    <TableHead>创建者</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <EmptyState
                          title="没有抑制规则"
                          description="当前没有抑制规则"
                          action={<Button onClick={handleCreate}>创建第一个抑制规则</Button>}
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
                        <TableCell className="text-sm">{rule.match_conditions.length} 条</TableCell>
                        <TableCell className="text-sm">{rule.duration ? `${rule.duration}s` : '永久'}</TableCell>
                        <TableCell className="text-sm text-gray-500 truncate max-w-xs">{rule.reason}</TableCell>
                        <TableCell className="text-sm">{rule.created_by}</TableCell>
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
            <CardTitle>被抑制告警</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>告警标题</TableHead>
                  <TableHead>规则名称</TableHead>
                  <TableHead>抑制原因</TableHead>
                  <TableHead>抑制时间</TableHead>
                  <TableHead>过期时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!alertsData || alertsData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <EmptyState title="没有被抑制的告警" description="当前没有被抑制的告警" />
                    </TableCell>
                  </TableRow>
                ) : (
                  alertsData.map((alert) => (
                    <TableRow key={alert.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{alert.alert_title}</TableCell>
                      <TableCell className="text-sm">{alert.rule_name}</TableCell>
                      <TableCell className="text-sm text-gray-500">{alert.reason}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(alert.suppressed_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {alert.expires_at ? new Date(alert.expires_at).toLocaleString() : '永久'}
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
            <DialogTitle>{isEditing ? '编辑抑制规则' : '创建抑制规则'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入抑制规则名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入抑制规则描述"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">抑制原因</label>
              <Input
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                placeholder="输入抑制原因"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">持续时间(秒)</label>
                <Input
                  type="number"
                  value={formData.duration}
                  onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) || 3600 })}
                  placeholder="3600 (留空表示永久)"
                />
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
