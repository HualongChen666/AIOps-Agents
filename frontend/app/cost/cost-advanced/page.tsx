'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { DollarSign, TrendingUp, TrendingDown, AlertTriangle, RefreshCw, Plus, Trash2, Settings, BarChart3, Target, FileText } from 'lucide-react';

interface Budget {
  id: string;
  name: string;
  service: string;
  amount: number;
  spent: number;
  remaining: number;
  period: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  status: 'on_track' | 'warning' | 'exceeded';
  alerts_enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface OptimizationSuggestion {
  id: string;
  resource: string;
  type: string;
  current_cost: number;
  projected_savings: number;
  effort: 'low' | 'medium' | 'high';
  impact: 'low' | 'medium' | 'high';
  description: string;
  status: 'pending' | 'implemented' | 'rejected';
  created_at: string;
}

interface CostAnomaly {
  id: string;
  resource_id: string;
  resource_type: string;
  anomaly_type: string;
  expected_cost: number;
  actual_cost: number;
  deviation: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  detected_at: string;
  status: 'open' | 'investigating' | 'resolved' | 'false_positive';
}

interface CostAlert {
  id: string;
  budget_id: string;
  alert_type: 'budget_exceeded' | 'forecast_exceeded' | 'anomaly_detected';
  threshold: number;
  current_value: number;
  severity: 'info' | 'warning' | 'critical';
  triggered_at: string;
  status: 'active' | 'acknowledged' | 'resolved';
}

export default function CostAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'budgets' | 'optimization' | 'anomalies'>('overview');
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [serviceFilter, setServiceFilter] = useState('all');
  const [newBudgetData, setNewBudgetData] = useState({
    name: '',
    service: '',
    amount: 0,
    period: 'monthly' as const,
    alerts_enabled: true,
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch cost overview
  const { data: costOverview, isLoading: overviewLoading, error: overviewError, refetch: refetchOverview } = useQuery<any>({
    queryKey: ['cost-overview'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/cost/overview');
      return resp.data;
    },
    refetchInterval: 300000,
  });

  // Fetch budgets
  const { data: budgets, isLoading: budgetsLoading, error: budgetsError, refetch: refetchBudgets } = useQuery<Budget[]>({
    queryKey: ['cost-budgets'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/cost/budgets');
      return resp.data.budgets || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch optimization suggestions
  const { data: optimizationSuggestions, isLoading: optimizationLoading, error: optimizationError, refetch: refetchOptimization } = useQuery<OptimizationSuggestion[]>({
    queryKey: ['cost-optimization'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/cost/optimization');
      return resp.data.suggestions || resp.data || [];
    },
    refetchInterval: 180000,
  });

  // Fetch cost anomalies
  const { data: costAnomalies, isLoading: anomaliesLoading, error: anomaliesError, refetch: refetchAnomalies } = useQuery<CostAnomaly[]>({
    queryKey: ['cost-anomalies'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/cost/anomalies');
      return resp.data.anomalies || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Create budget mutation
  const createBudgetMutation = useMutation({
    mutationFn: async (budgetData: typeof newBudgetData) => {
      const resp = await api.post('/api/v1/cost/budgets', budgetData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Budget created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['cost-budgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to create budget: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete budget mutation
  const deleteBudgetMutation = useMutation({
    mutationFn: async (budgetId: string) => {
      const resp = await api.delete(`/api/v1/cost/budgets/${budgetId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Budget deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['cost-budgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete budget: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (budgetsError) {
      setPageError(budgetsError as Error);
      showError('Failed to load cost data');
    }
  }, [budgetsError, setPageError, showError]);

  const filteredBudgets = budgets?.filter((budget) => {
    if (serviceFilter !== 'all' && budget.service !== serviceFilter) return false;
    if (debouncedSearch && !budget.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on_track':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'exceeded':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
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
      case 'info':
        return 'bg-blue-100 text-blue-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateBudget = () => {
    if (!newBudgetData.name || !newBudgetData.service || newBudgetData.amount <= 0) {
      showError('Please fill in all required fields');
      return;
    }
    createBudgetMutation.mutate(newBudgetData);
  };

  const handleDeleteBudget = (budgetId: string) => {
    if (!window.confirm('Are you sure you want to delete this budget?')) return;
    deleteBudgetMutation.mutate(budgetId);
  };

  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载成本数据，请稍后重试"
          action={<Button onClick={() => refetchBudgets()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchBudgets()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <DollarSign className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">成本管理高级</h1>
            <p className="text-sm text-gray-500">成本分析、预算管理、优化建议和异常检测</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchBudgets()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建预算
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">
            <BarChart3 className="h-4 w-4 mr-2" />
            概览
          </TabsTrigger>
          <TabsTrigger value="budgets">
            <Target className="h-4 w-4 mr-2" />
            预算
          </TabsTrigger>
          <TabsTrigger value="optimization">
            <TrendingDown className="h-4 w-4 mr-2" />
            优化建议
          </TabsTrigger>
          <TabsTrigger value="anomalies">
            <AlertTriangle className="h-4 w-4 mr-2" />
            异常检测
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {costOverview ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">总成本</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-gray-900">${costOverview.total_cost?.toFixed(2) || '0.00'}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">本月成本</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-blue-600">${costOverview.monthly_cost?.toFixed(2) || '0.00'}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">预计节省</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-green-600">${costOverview.projected_savings?.toFixed(2) || '0.00'}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">预算状态</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-yellow-600">{costOverview.budget_status || 'N/A'}</div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>成本趋势</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 flex items-center justify-center text-gray-500">
                    成本趋势图表区域
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <EmptyState title="无概览数据" description="暂无成本概览数据" />
          )}
        </TabsContent>

        <TabsContent value="budgets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  预算管理
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索预算..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={serviceFilter} onChange={(e) => setServiceFilter(e.target.value)}>
                    <option value="all">全部服务</option>
                    <option value="Amazon EC2">Amazon EC2</option>
                    <option value="Amazon S3">Amazon S3</option>
                    <option value="Amazon RDS">Amazon RDS</option>
                    <option value="Azure">Azure</option>
                    <option value="Google Cloud">Google Cloud</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {budgetsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredBudgets.length === 0 ? (
                <EmptyState
                  title="没有预算"
                  description="点击创建预算开始成本管理"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建预算</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>服务</TableHead>
                      <TableHead>预算金额</TableHead>
                      <TableHead>已使用</TableHead>
                      <TableHead>剩余</TableHead>
                      <TableHead>周期</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>告警</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredBudgets.map((budget) => (
                      <TableRow key={budget.id}>
                        <TableCell className="font-mono text-sm">{budget.id}</TableCell>
                        <TableCell className="font-medium">{budget.name}</TableCell>
                        <TableCell>{budget.service}</TableCell>
                        <TableCell className="font-medium">${budget.amount.toFixed(2)}</TableCell>
                        <TableCell className="text-blue-600">${budget.spent.toFixed(2)}</TableCell>
                        <TableCell className={budget.remaining < 0 ? 'text-red-600' : 'text-green-600'}>
                          ${budget.remaining.toFixed(2)}
                        </TableCell>
                        <TableCell className="capitalize">{budget.period}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(budget.status)}>
                            {budget.status.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {budget.alerts_enabled ? (
                            <Badge className="bg-green-100 text-green-800">启用</Badge>
                          ) : (
                            <Badge className="bg-gray-100 text-gray-800">禁用</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(budget.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedBudget(budget)}
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteBudget(budget.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="optimization" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingDown className="h-5 w-5" />
                优化建议
              </CardTitle>
            </CardHeader>
            <CardContent>
              {optimizationLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !optimizationSuggestions || optimizationSuggestions.length === 0 ? (
                <EmptyState title="无优化建议" description="暂无优化建议记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资源</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>当前成本</TableHead>
                      <TableHead>预计节省</TableHead>
                      <TableHead>工作量</TableHead>
                      <TableHead>影响</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {optimizationSuggestions.map((suggestion) => (
                      <TableRow key={suggestion.id}>
                        <TableCell className="font-mono text-sm">{suggestion.id}</TableCell>
                        <TableCell className="font-medium">{suggestion.resource}</TableCell>
                        <TableCell>{suggestion.type}</TableCell>
                        <TableCell>${suggestion.current_cost.toFixed(2)}</TableCell>
                        <TableCell className="font-medium text-green-600">${suggestion.projected_savings.toFixed(2)}</TableCell>
                        <TableCell>
                          <Badge className={getEffortColor(suggestion.effort)}>
                            {suggestion.effort}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getEffortColor(suggestion.impact)}>
                            {suggestion.impact}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={suggestion.status === 'implemented' ? 'bg-green-100 text-green-800' : suggestion.status === 'rejected' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}>
                            {suggestion.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            应用
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="anomalies" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                异常检测
              </CardTitle>
            </CardHeader>
            <CardContent>
              {anomaliesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !costAnomalies || costAnomalies.length === 0 ? (
                <EmptyState title="无异常" description="暂无成本异常记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资源ID</TableHead>
                      <TableHead>资源类型</TableHead>
                      <TableHead>异常类型</TableHead>
                      <TableHead>预期成本</TableHead>
                      <TableHead>实际成本</TableHead>
                      <TableHead>偏差</TableHead>
                      <TableHead>严重度</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>检测时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {costAnomalies.map((anomaly) => (
                      <TableRow key={anomaly.id}>
                        <TableCell className="font-mono text-sm">{anomaly.id}</TableCell>
                        <TableCell className="font-mono text-sm">{anomaly.resource_id}</TableCell>
                        <TableCell>{anomaly.resource_type}</TableCell>
                        <TableCell>{anomaly.anomaly_type}</TableCell>
                        <TableCell>${anomaly.expected_cost.toFixed(2)}</TableCell>
                        <TableCell className="text-red-600">${anomaly.actual_cost.toFixed(2)}</TableCell>
                        <TableCell className={anomaly.deviation > 0 ? 'text-red-600' : 'text-green-600'}>
                          {anomaly.deviation.toFixed(1)}%
                        </TableCell>
                        <TableCell>
                          <Badge className={getSeverityColor(anomaly.severity)}>
                            {anomaly.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={anomaly.status === 'resolved' ? 'bg-green-100 text-green-800' : anomaly.status === 'false_positive' ? 'bg-gray-100 text-gray-800' : 'bg-yellow-100 text-yellow-800'}>
                            {anomaly.status.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(anomaly.detected_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            调查
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建预算</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">预算名称</label>
              <Input
                value={newBudgetData.name}
                onChange={(e) => setNewBudgetData({ ...newBudgetData, name: e.target.value })}
                placeholder="输入预算名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
              <Input
                value={newBudgetData.service}
                onChange={(e) => setNewBudgetData({ ...newBudgetData, service: e.target.value })}
                placeholder="例如: Amazon EC2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">预算金额</label>
              <Input
                type="number"
                value={newBudgetData.amount}
                onChange={(e) => setNewBudgetData({ ...newBudgetData, amount: parseFloat(e.target.value) })}
                placeholder="预算金额"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">周期</label>
              <Select
                value={newBudgetData.period}
                onChange={(e) => setNewBudgetData({ ...newBudgetData, period: e.target.value as any })}
              >
                <option value="daily">每日</option>
                <option value="weekly">每周</option>
                <option value="monthly">每月</option>
                <option value="quarterly">每季度</option>
                <option value="yearly">每年</option>
              </Select>
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={newBudgetData.alerts_enabled}
                onChange={(e) => setNewBudgetData({ ...newBudgetData, alerts_enabled: e.target.checked })}
              />
              <span className="text-sm">启用告警</span>
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateBudget} disabled={createBudgetMutation.isPending}>
              {createBudgetMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
