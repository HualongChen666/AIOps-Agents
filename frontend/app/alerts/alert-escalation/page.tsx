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
import { ArrowUp, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface EscalationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  match_conditions: Array<{
    field: string;
    operator: string;
    value: string;
  }>;
  escalation_levels: Array<{
    level: number;
    wait_time: number;
    targets: string[];
    notification_method: 'email' | 'slack' | 'pagerduty' | 'sms';
  }>;
  max_escalation_level: number;
  created_at: string;
  updated_at: string;
}

interface EscalationRecord {
  id: string;
  alert_id: string;
  alert_title: string;
  rule_id: string;
  rule_name: string;
  current_level: number;
  escalated_at: string;
  next_escalation_at?: string;
  status: 'active' | 'completed' | 'cancelled';
}

export default function AlertEscalationPage() {
  const [selectedRule, setSelectedRule] = useState<EscalationRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'records'>('rules');
  const [filters, setFilters] = useState({
    enabled: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<EscalationRule>>({
    name: '',
    description: '',
    enabled: true,
    match_conditions: [],
    escalation_levels: [],
    max_escalation_level: 3,
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: rulesData, isLoading: rulesLoading, error: rulesError, refetch: refetchRules } = useQuery<EscalationRule[]>({
    queryKey: ['escalation-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/escalation/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: recordsData, isLoading: recordsLoading, refetch: refetchRecords } = useQuery<EscalationRecord[]>({
    queryKey: ['escalation-records'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/escalation/records');
      return resp.data.records || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createRuleMutation = useMutation({
    mutationFn: async (data: Partial<EscalationRule>) => {
      const resp = await api.post('/api/v1/alerts/escalation/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('升级规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['escalation-rules'] });
    },
    onError: () => showError('创建升级规则失败'),
  });

  const updateRuleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<EscalationRule> }) => {
      const resp = await api.put(`/api/v1/alerts/escalation/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('升级规则更新成功');
      setShowDialog(false);
      setSelectedRule(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['escalation-rules'] });
    },
    onError: () => showError('更新升级规则失败'),
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/escalation/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('升级规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['escalation-rules'] });
    },
    onError: () => showError('删除升级规则失败'),
  });

  useEffect(() => {
    if (rulesError) showError('Failed to load escalation rules');
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
      escalation_levels: [],
      max_escalation_level: 3,
    });
    setShowDialog(true);
  };

  const handleEdit = (rule: EscalationRule) => {
    setIsEditing(true);
    setSelectedRule(rule);
    setFormData(rule);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此升级规则吗？')) return;
    deleteRuleMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedRule) {
      updateRuleMutation.mutate({ id: selectedRule.id, data: formData });
    } else {
      createRuleMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (rule: EscalationRule) => {
    updateRuleMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } });
  };

  if (rulesLoading || recordsLoading) {
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
          <ArrowUp className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警升级</h1>
            <p className="text-sm text-gray-500">配置告警升级规则以自动升级未处理的告警</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建升级规则
          </Button>
          <Button onClick={() => { refetchRules(); refetchRecords(); }} variant="outline">
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
              升级规则
            </button>
            <button
              onClick={() => setActiveTab('records')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'records' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              升级记录 ({recordsData?.length || 0})
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
              <CardTitle>升级规则 ({filteredRules.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>匹配条件</TableHead>
                    <TableHead>升级级别</TableHead>
                    <TableHead>最大级别</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <EmptyState
                          title="没有升级规则"
                          description="当前没有升级规则"
                          action={<Button onClick={handleCreate}>创建第一个升级规则</Button>}
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
                        <TableCell className="text-sm">{rule.escalation_levels.length} 级</TableCell>
                        <TableCell className="text-sm font-mono">{rule.max_escalation_level}</TableCell>
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

      {activeTab === 'records' && (
        <Card>
          <CardHeader>
            <CardTitle>升级记录</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>告警标题</TableHead>
                  <TableHead>规则名称</TableHead>
                  <TableHead>当前级别</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>升级时间</TableHead>
                  <TableHead>下次升级</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!recordsData || recordsData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <EmptyState title="没有升级记录" description="当前没有升级记录" />
                    </TableCell>
                  </TableRow>
                ) : (
                  recordsData.map((record) => (
                    <TableRow key={record.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{record.alert_title}</TableCell>
                      <TableCell className="text-sm">{record.rule_name}</TableCell>
                      <TableCell className="text-sm font-mono">Level {record.current_level}</TableCell>
                      <TableCell>
                        <Badge className={record.status === 'active' ? 'bg-red-100 text-red-800' : record.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                          {record.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(record.escalated_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {record.next_escalation_at ? new Date(record.next_escalation_at).toLocaleString() : '-'}
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
            <DialogTitle>{isEditing ? '编辑升级规则' : '创建升级规则'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入升级规则名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入升级规则描述"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">最大升级级别</label>
                <Input
                  type="number"
                  value={formData.max_escalation_level}
                  onChange={(e) => setFormData({ ...formData, max_escalation_level: parseInt(e.target.value) || 3 })}
                  placeholder="3"
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
