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
import { Filter, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface DeduplicationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  dedup_field: string;
  dedup_window: number;
  match_conditions: Array<{
    field: string;
    operator: string;
    value: string;
  }>;
  created_at: string;
  updated_at: string;
}

interface DeduplicationStats {
  total_alerts: number;
  deduplicated_alerts: number;
  dedup_rate: number;
  saved_notifications: number;
}

export default function AlertDeduplicationPage() {
  const [selectedRule, setSelectedRule] = useState<DeduplicationRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'stats'>('rules');
  const [filters, setFilters] = useState({
    enabled: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<DeduplicationRule>>({
    name: '',
    description: '',
    enabled: true,
    dedup_field: 'fingerprint',
    dedup_window: 300,
    match_conditions: [],
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: rulesData, isLoading: rulesLoading, error: rulesError, refetch: refetchRules } = useQuery<DeduplicationRule[]>({
    queryKey: ['deduplication-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/deduplication/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery<DeduplicationStats>({
    queryKey: ['deduplication-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/deduplication/stats');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const createRuleMutation = useMutation({
    mutationFn: async (data: Partial<DeduplicationRule>) => {
      const resp = await api.post('/api/v1/alerts/deduplication/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['deduplication-rules'] });
    },
    onError: () => showError('创建规则失败'),
  });

  const updateRuleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<DeduplicationRule> }) => {
      const resp = await api.put(`/api/v1/alerts/deduplication/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则更新成功');
      setShowDialog(false);
      setSelectedRule(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['deduplication-rules'] });
    },
    onError: () => showError('更新规则失败'),
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/deduplication/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['deduplication-rules'] });
    },
    onError: () => showError('删除规则失败'),
  });

  useEffect(() => {
    if (rulesError) showError('Failed to load deduplication rules');
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
      dedup_field: 'fingerprint',
      dedup_window: 300,
      match_conditions: [],
    });
    setShowDialog(true);
  };

  const handleEdit = (rule: DeduplicationRule) => {
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

  const handleToggleEnabled = async (rule: DeduplicationRule) => {
    updateRuleMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } });
  };

  if (rulesLoading || statsLoading) {
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
          <Filter className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警去重</h1>
            <p className="text-sm text-gray-500">配置告警去重规则以减少重复告警</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建规则
          </Button>
          <Button onClick={() => { refetchRules(); refetchStats(); }} variant="outline">
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
              去重规则
            </button>
            <button
              onClick={() => setActiveTab('stats')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'stats' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              统计信息
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
              <CardTitle>去重规则 ({filteredRules.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>去重字段</TableHead>
                    <TableHead>时间窗口</TableHead>
                    <TableHead>匹配条件</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <EmptyState
                          title="没有规则"
                          description="当前没有符合条件的去重规则"
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
                        <TableCell className="text-sm font-mono">{rule.dedup_field}</TableCell>
                        <TableCell className="text-sm">{rule.dedup_window}s</TableCell>
                        <TableCell className="text-sm">{rule.match_conditions.length} 条</TableCell>
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

      {activeTab === 'stats' && statsData && (
        <Card>
          <CardHeader>
            <CardTitle>去重统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">总告警数</div>
                <div className="text-2xl font-bold text-[var(--accent-blue)]">{statsData.total_alerts}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">去重告警数</div>
                <div className="text-2xl font-bold text-[var(--accent-green)]">{statsData.deduplicated_alerts}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">去重率</div>
                <div className="text-2xl font-bold text-[var(--accent-yellow)]">{statsData.dedup_rate.toFixed(2)}%</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">节省通知数</div>
                <div className="text-2xl font-bold text-[var(--accent-cyan)]">{statsData.saved_notifications}</div>
              </div>
            </div>
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
                <label className="block text-sm font-medium text-gray-700 mb-1">去重字段</label>
                <Input
                  value={formData.dedup_field}
                  onChange={(e) => setFormData({ ...formData, dedup_field: e.target.value })}
                  placeholder="例如: fingerprint"
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">时间窗口(秒)</label>
              <Input
                type="number"
                value={formData.dedup_window}
                onChange={(e) => setFormData({ ...formData, dedup_window: parseInt(e.target.value) || 300 })}
                placeholder="300"
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
