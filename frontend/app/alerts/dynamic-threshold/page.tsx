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
import { TrendingUp, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw, Activity } from 'lucide-react';

interface DynamicThreshold {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  metric: string;
  algorithm: 'moving_average' | 'exponential_smoothing' | 'anomaly_detection' | 'percentile';
  window_size: number;
  sensitivity: number;
  min_threshold: number;
  max_threshold: number;
  adaptation_rate: number;
  labels: Record<string, string>;
  created_at: string;
  updated_at: string;
}

interface ThresholdValue {
  metric: string;
  current_value: number;
  dynamic_threshold: number;
  static_threshold: number;
  is_alerting: boolean;
  timestamp: string;
}

export default function DynamicThresholdPage() {
  const [selectedThreshold, setSelectedThreshold] = useState<DynamicThreshold | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'values'>('rules');
  const [filters, setFilters] = useState({
    enabled: 'all',
    algorithm: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<DynamicThreshold>>({
    name: '',
    description: '',
    enabled: true,
    metric: '',
    algorithm: 'moving_average',
    window_size: 300,
    sensitivity: 0.5,
    min_threshold: 0,
    max_threshold: 100,
    adaptation_rate: 0.1,
    labels: {},
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: thresholdsData, isLoading: thresholdsLoading, error: thresholdsError, refetch: refetchThresholds } = useQuery<DynamicThreshold[]>({
    queryKey: ['dynamic-thresholds'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/dynamic-threshold/rules');
      return resp.data.thresholds || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: valuesData, isLoading: valuesLoading, refetch: refetchValues } = useQuery<ThresholdValue[]>({
    queryKey: ['dynamic-threshold-values'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/dynamic-threshold/values');
      return resp.data.values || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createThresholdMutation = useMutation({
    mutationFn: async (data: Partial<DynamicThreshold>) => {
      const resp = await api.post('/api/v1/alerts/dynamic-threshold/rules', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('阈值规则创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['dynamic-thresholds'] });
    },
    onError: () => showError('创建阈值规则失败'),
  });

  const updateThresholdMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<DynamicThreshold> }) => {
      const resp = await api.put(`/api/v1/alerts/dynamic-threshold/rules/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('阈值规则更新成功');
      setShowDialog(false);
      setSelectedThreshold(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['dynamic-thresholds'] });
    },
    onError: () => showError('更新阈值规则失败'),
  });

  const deleteThresholdMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/dynamic-threshold/rules/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('阈值规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['dynamic-thresholds'] });
    },
    onError: () => showError('删除阈值规则失败'),
  });

  useEffect(() => {
    if (thresholdsError) showError('Failed to load dynamic thresholds');
  }, [thresholdsError, showError]);

  const filteredThresholds = (thresholdsData || []).filter((threshold) => {
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !threshold.enabled : threshold.enabled)) return false;
    if (filters.algorithm !== 'all' && threshold.algorithm !== filters.algorithm) return false;
    if (debouncedSearch && !threshold.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      description: '',
      enabled: true,
      metric: '',
      algorithm: 'moving_average',
      window_size: 300,
      sensitivity: 0.5,
      min_threshold: 0,
      max_threshold: 100,
      adaptation_rate: 0.1,
      labels: {},
    });
    setShowDialog(true);
  };

  const handleEdit = (threshold: DynamicThreshold) => {
    setIsEditing(true);
    setSelectedThreshold(threshold);
    setFormData(threshold);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此阈值规则吗？')) return;
    deleteThresholdMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedThreshold) {
      updateThresholdMutation.mutate({ id: selectedThreshold.id, data: formData });
    } else {
      createThresholdMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (threshold: DynamicThreshold) => {
    updateThresholdMutation.mutate({ id: threshold.id, data: { enabled: !threshold.enabled } });
  };

  const getAlgorithmColor = (algorithm: string) => {
    const colors: Record<string, string> = {
      moving_average: 'bg-blue-100 text-blue-800',
      exponential_smoothing: 'bg-green-100 text-green-800',
      anomaly_detection: 'bg-purple-100 text-purple-800',
      percentile: 'bg-orange-100 text-orange-800',
    };
    return colors[algorithm] || 'bg-gray-100 text-gray-800';
  };

  if (thresholdsLoading || valuesLoading) {
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
          <TrendingUp className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">动态阈值</h1>
            <p className="text-sm text-gray-500">配置动态阈值规则以适应业务变化</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建规则
          </Button>
          <Button onClick={() => { refetchThresholds(); refetchValues(); }} variant="outline">
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
              阈值规则
            </button>
            <button
              onClick={() => setActiveTab('values')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'values' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              实时值 ({valuesData?.length || 0})
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">算法</label>
                  <Select
                    value={filters.algorithm}
                    onChange={(e) => setFilters({ ...filters, algorithm: e.target.value })}
                  >
                    <option value="all">全部</option>
                    <option value="moving_average">移动平均</option>
                    <option value="exponential_smoothing">指数平滑</option>
                    <option value="anomaly_detection">异常检测</option>
                    <option value="percentile">百分位数</option>
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
              <CardTitle>阈值规则 ({filteredThresholds.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>指标</TableHead>
                    <TableHead>算法</TableHead>
                    <TableHead>窗口大小</TableHead>
                    <TableHead>敏感度</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredThresholds.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <EmptyState
                          title="没有规则"
                          description="当前没有符合条件的动态阈值规则"
                          action={<Button onClick={handleCreate}>创建第一个规则</Button>}
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredThresholds.map((threshold) => (
                      <TableRow key={threshold.id} className="cursor-pointer hover:bg-gray-50">
                        <TableCell className="font-medium">{threshold.name}</TableCell>
                        <TableCell>
                          <Badge className={threshold.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {threshold.enabled ? '已启用' : '已禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm font-mono">{threshold.metric}</TableCell>
                        <TableCell>
                          <Badge className={getAlgorithmColor(threshold.algorithm)}>
                            {threshold.algorithm}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">{threshold.window_size}s</TableCell>
                        <TableCell className="text-sm">{threshold.sensitivity}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleToggleEnabled(threshold)}>
                              {threshold.enabled ? '禁用' : '启用'}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(threshold)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(threshold.id)}>
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

      {activeTab === 'values' && (
        <Card>
          <CardHeader>
            <CardTitle>实时阈值值</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>指标</TableHead>
                  <TableHead>当前值</TableHead>
                  <TableHead>动态阈值</TableHead>
                  <TableHead>静态阈值</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!valuesData || valuesData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <EmptyState title="没有数据" description="当前没有实时阈值数据" />
                    </TableCell>
                  </TableRow>
                ) : (
                  valuesData.map((value) => (
                    <TableRow key={value.metric} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-mono text-sm">{value.metric}</TableCell>
                      <TableCell className="font-mono text-sm">{value.current_value.toFixed(2)}</TableCell>
                      <TableCell className="font-mono text-sm">{value.dynamic_threshold.toFixed(2)}</TableCell>
                      <TableCell className="font-mono text-sm">{value.static_threshold.toFixed(2)}</TableCell>
                      <TableCell>
                        <Badge className={value.is_alerting ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}>
                          {value.is_alerting ? '告警' : '正常'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(value.timestamp).toLocaleString()}
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
                <label className="block text-sm font-medium text-gray-700 mb-1">指标</label>
                <Input
                  value={formData.metric}
                  onChange={(e) => setFormData({ ...formData, metric: e.target.value })}
                  placeholder="例如: cpu_usage"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">算法</label>
                <Select
                  value={formData.algorithm}
                  onChange={(e) => setFormData({ ...formData, algorithm: e.target.value as any })}
                >
                  <option value="moving_average">移动平均</option>
                  <option value="exponential_smoothing">指数平滑</option>
                  <option value="anomaly_detection">异常检测</option>
                  <option value="percentile">百分位数</option>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">窗口大小(秒)</label>
                <Input
                  type="number"
                  value={formData.window_size}
                  onChange={(e) => setFormData({ ...formData, window_size: parseInt(e.target.value) || 300 })}
                  placeholder="300"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">敏感度</label>
                <Input
                  type="number"
                  step="0.1"
                  value={formData.sensitivity}
                  onChange={(e) => setFormData({ ...formData, sensitivity: parseFloat(e.target.value) || 0.5 })}
                  placeholder="0.5"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">最小阈值</label>
                <Input
                  type="number"
                  value={formData.min_threshold}
                  onChange={(e) => setFormData({ ...formData, min_threshold: parseFloat(e.target.value) || 0 })}
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">最大阈值</label>
                <Input
                  type="number"
                  value={formData.max_threshold}
                  onChange={(e) => setFormData({ ...formData, max_threshold: parseFloat(e.target.value) || 100 })}
                  placeholder="100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">适应率</label>
                <Input
                  type="number"
                  step="0.1"
                  value={formData.adaptation_rate}
                  onChange={(e) => setFormData({ ...formData, adaptation_rate: parseFloat(e.target.value) || 0.1 })}
                  placeholder="0.1"
                />
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
            <Button onClick={handleSave} disabled={createThresholdMutation.isPending || updateThresholdMutation.isPending}>
              {isEditing ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
