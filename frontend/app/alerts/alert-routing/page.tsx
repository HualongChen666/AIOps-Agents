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
import { Route, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw, ArrowRight } from 'lucide-react';

interface AlertRoute {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  priority: number;
  match_conditions: Array<{
    field: string;
    operator: string;
    value: string;
  }>;
  target: {
    type: 'email' | 'slack' | 'webhook' | 'pagerduty' | 'teams';
    endpoint: string;
    config?: Record<string, any>;
  };
  rate_limit: {
    enabled: boolean;
    max_per_hour: number;
  };
  created_at: string;
  updated_at: string;
}

export default function AlertRoutingPage() {
  const [selectedRoute, setSelectedRoute] = useState<AlertRoute | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [filters, setFilters] = useState({
    enabled: 'all',
    targetType: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<AlertRoute>>({
    name: '',
    description: '',
    enabled: true,
    priority: 0,
    match_conditions: [],
    target: {
      type: 'email',
      endpoint: '',
      config: {},
    },
    rate_limit: {
      enabled: false,
      max_per_hour: 10,
    },
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  // 获取告警路由列表
  const { data: routesData, isLoading: routesLoading, error: routesError, refetch: refetchRoutes } = useQuery<AlertRoute[]>({
    queryKey: ['alert-routes'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/routing');
      return resp.data.routes || resp.data || [];
    },
    refetchInterval: 30000, // 30秒刷新
  });

  // 创建路由
  const createRouteMutation = useMutation({
    mutationFn: async (data: Partial<AlertRoute>) => {
      const resp = await api.post('/api/v1/alerts/routing', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('路由创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['alert-routes'] });
    },
    onError: () => {
      showError('创建路由失败');
    },
  });

  // 更新路由
  const updateRouteMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<AlertRoute> }) => {
      const resp = await api.put(`/api/v1/alerts/routing/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('路由更新成功');
      setShowDialog(false);
      setSelectedRoute(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['alert-routes'] });
    },
    onError: () => {
      showError('更新路由失败');
    },
  });

  // 删除路由
  const deleteRouteMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/routing/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('路由删除成功');
      queryClient.invalidateQueries({ queryKey: ['alert-routes'] });
    },
    onError: () => {
      showError('删除路由失败');
    },
  });

  useEffect(() => {
    if (routesError) {
      showError('Failed to load alert routes');
    }
  }, [routesError, showError]);

  const filteredRoutes = (routesData || []).filter((route) => {
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !route.enabled : route.enabled)) return false;
    if (filters.targetType !== 'all' && route.target.type !== filters.targetType) return false;
    if (debouncedSearch && !route.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      description: '',
      enabled: true,
      priority: 0,
      match_conditions: [],
      target: {
        type: 'email',
        endpoint: '',
        config: {},
      },
      rate_limit: {
        enabled: false,
        max_per_hour: 10,
      },
    });
    setShowDialog(true);
  };

  const handleEdit = (route: AlertRoute) => {
    setIsEditing(true);
    setSelectedRoute(route);
    setFormData(route);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此路由吗？')) return;
    deleteRouteMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedRoute) {
      updateRouteMutation.mutate({ id: selectedRoute.id, data: formData });
    } else {
      createRouteMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (route: AlertRoute) => {
    updateRouteMutation.mutate({ id: route.id, data: { enabled: !route.enabled } });
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

  if (routesLoading) {
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
          <Route className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警路由</h1>
            <p className="text-sm text-gray-500">配置告警路由规则和目标</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建路由
          </Button>
          <Button onClick={() => refetchRoutes()} variant="outline">
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
              <label className="block text-sm font-medium text-gray-700 mb-1">目标类型</label>
              <Select
                value={filters.targetType}
                onChange={(e) => setFilters({ ...filters, targetType: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="email">邮件</option>
                <option value="slack">Slack</option>
                <option value="webhook">Webhook</option>
                <option value="pagerduty">PagerDuty</option>
                <option value="teams">Teams</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <Input
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="搜索路由名称"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 路由列表 */}
      <Card>
        <CardHeader>
          <CardTitle>路由列表 ({filteredRoutes.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>目标类型</TableHead>
                <TableHead>目标端点</TableHead>
                <TableHead>匹配条件</TableHead>
                <TableHead>限流</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRoutes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState
                      title="没有路由"
                      description="当前没有符合条件的告警路由"
                      action={<Button onClick={handleCreate}>创建第一个路由</Button>}
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredRoutes.map((route) => (
                  <TableRow key={route.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{route.name}</TableCell>
                    <TableCell className="font-mono text-sm">{route.priority}</TableCell>
                    <TableCell>
                      <Badge className={route.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {route.enabled ? '已启用' : '已禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getTargetTypeColor(route.target.type)}>
                        {route.target.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500 truncate max-w-xs">{route.target.endpoint}</TableCell>
                    <TableCell className="text-sm">{route.match_conditions.length} 条</TableCell>
                    <TableCell>
                      <Badge className={route.rate_limit.enabled ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}>
                        {route.rate_limit.enabled ? `${route.rate_limit.max_per_hour}/h` : '无'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleEnabled(route)}
                        >
                          {route.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(route)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(route.id)}
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
            <DialogTitle>{isEditing ? '编辑路由' : '创建路由'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入路由名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入路由描述"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
                <Input
                  type="number"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                  placeholder="数字越大优先级越高"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">目标类型</label>
              <Select
                value={formData.target?.type}
                onChange={(e) => setFormData({ ...formData, target: { ...formData.target!, type: e.target.value as any, endpoint: formData.target?.endpoint || '' } })}
              >
                <option value="email">邮件</option>
                <option value="slack">Slack</option>
                <option value="webhook">Webhook</option>
                <option value="pagerduty">PagerDuty</option>
                <option value="teams">Teams</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">目标端点</label>
              <Input
                value={formData.target?.endpoint}
                onChange={(e) => setFormData({ ...formData, target: { ...formData.target!, endpoint: e.target.value } })}
                placeholder="例如: https://hooks.slack.com/..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用限流</label>
                <Select
                  value={formData.rate_limit?.enabled ? 'true' : 'false'}
                  onChange={(e) => setFormData({ ...formData, rate_limit: { ...formData.rate_limit!, enabled: e.target.value === 'true' } })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">每小时最大数量</label>
                <Input
                  type="number"
                  value={formData.rate_limit?.max_per_hour}
                  onChange={(e) => setFormData({ ...formData, rate_limit: { ...formData.rate_limit!, max_per_hour: parseInt(e.target.value) || 10 } })}
                  placeholder="10"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={createRouteMutation.isPending || updateRouteMutation.isPending}>
              {isEditing ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
