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
import { TrendingUp, Cpu, HardDrive, Activity, RefreshCw, Plus, Trash2, Settings, BarChart3, Target, Zap } from 'lucide-react';

interface CapacityPlan {
  id: string;
  name: string;
  resource_type: 'cpu' | 'memory' | 'disk' | 'network' | 'gpu' | 'storage';
  planning_horizon: 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  current_capacity: number;
  projected_demand: number;
  recommended_capacity: number;
  confidence: number;
  created_at: string;
  status: 'active' | 'archived';
}

interface CapacityForecast {
  id: string;
  resource_type: string;
  forecast_period: string;
  predictions: Array<{ date: string; value: number; confidence: number }>;
  model_used: string;
  accuracy: number;
  created_at: string;
}

interface OptimizationResult {
  id: string;
  resource_id: string;
  resource_type: string;
  current_utilization: number;
  potential_savings: number;
  optimization_strategy: string;
  effort_level: 'low' | 'medium' | 'high';
  impact_level: 'low' | 'medium' | 'high';
  status: 'pending' | 'implemented' | 'rejected';
  created_at: string;
}

interface RightsizingRecommendation {
  id: string;
  resource_id: string;
  resource_type: string;
  current_spec: string;
  recommended_spec: string;
  action: 'scale_up' | 'scale_down' | 'scale_out' | 'scale_in' | 'no_action';
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimated_savings: number;
  created_at: string;
}

export default function CapacityAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'planning' | 'forecasts' | 'optimization' | 'rightsizing'>('planning');
  const [selectedPlan, setSelectedPlan] = useState<CapacityPlan | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [resourceFilter, setResourceFilter] = useState('all');

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch capacity plans
  const { data: capacityPlans, isLoading: plansLoading, error: plansError, refetch: refetchPlans } = useQuery<CapacityPlan[]>({
    queryKey: ['capacity-plans'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/capacity/planning');
      return resp.data.plans || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch capacity forecasts
  const { data: capacityForecasts, isLoading: forecastsLoading, error: forecastsError, refetch: refetchForecasts } = useQuery<CapacityForecast[]>({
    queryKey: ['capacity-forecasts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/capacity/forecasts');
      return resp.data.forecasts || resp.data || [];
    },
    refetchInterval: 300000,
  });

  // Fetch optimization results
  const { data: optimizationResults, isLoading: optimizationLoading, error: optimizationError, refetch: refetchOptimization } = useQuery<OptimizationResult[]>({
    queryKey: ['capacity-optimization'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/capacity/optimization');
      return resp.data.results || resp.data || [];
    },
    refetchInterval: 180000,
  });

  // Fetch rightsizing recommendations
  const { data: rightsizingRecommendations, isLoading: rightsizingLoading, error: rightsizingError, refetch: refetchRightsizing } = useQuery<RightsizingRecommendation[]>({
    queryKey: ['capacity-rightsizing'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/capacity/rightsizing');
      return resp.data.recommendations || resp.data || [];
    },
    refetchInterval: 180000,
  });

  // Delete plan mutation
  const deletePlanMutation = useMutation({
    mutationFn: async (planId: string) => {
      const resp = await api.delete(`/api/v1/capacity/planning/${planId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Plan deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['capacity-plans'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete plan: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (plansError) {
      setPageError(plansError as Error);
      showError('Failed to load capacity plans');
    }
  }, [plansError, setPageError, showError]);

  const filteredPlans = capacityPlans?.filter((plan) => {
    if (resourceFilter !== 'all' && plan.resource_type !== resourceFilter) return false;
    if (debouncedSearch && !plan.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'cpu':
        return <Cpu className="h-4 w-4" />;
      case 'memory':
        return <Activity className="h-4 w-4" />;
      case 'disk':
      case 'storage':
        return <HardDrive className="h-4 w-4" />;
      default:
        return <TrendingUp className="h-4 w-4" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
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

  const getActionColor = (action: string) => {
    switch (action) {
      case 'scale_up':
        return 'bg-blue-100 text-blue-800';
      case 'scale_down':
        return 'bg-green-100 text-green-800';
      case 'scale_out':
        return 'bg-purple-100 text-purple-800';
      case 'scale_in':
        return 'bg-orange-100 text-orange-800';
      case 'no_action':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleDeletePlan = (planId: string) => {
    if (!window.confirm('Are you sure you want to delete this plan?')) return;
    deletePlanMutation.mutate(planId);
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
          description="无法加载容量规划数据，请稍后重试"
          action={<Button onClick={() => refetchPlans()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchPlans()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">容量规划高级</h1>
            <p className="text-sm text-gray-500">容量规划、预测、优化和调整建议</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchPlans()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建计划
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="planning">
            <BarChart3 className="h-4 w-4 mr-2" />
            容量规划
          </TabsTrigger>
          <TabsTrigger value="forecasts">
            <TrendingUp className="h-4 w-4 mr-2" />
            预测分析
          </TabsTrigger>
          <TabsTrigger value="optimization">
            <Zap className="h-4 w-4 mr-2" />
            优化建议
          </TabsTrigger>
          <TabsTrigger value="rightsizing">
            <Target className="h-4 w-4 mr-2" />
            调整建议
          </TabsTrigger>
        </TabsList>

        <TabsContent value="planning" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  容量规划
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索计划..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={resourceFilter} onChange={(e) => setResourceFilter(e.target.value)}>
                    <option value="all">全部资源</option>
                    <option value="cpu">CPU</option>
                    <option value="memory">内存</option>
                    <option value="disk">磁盘</option>
                    <option value="network">网络</option>
                    <option value="gpu">GPU</option>
                    <option value="storage">存储</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {plansLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredPlans.length === 0 ? (
                <EmptyState
                  title="没有容量规划"
                  description="点击创建计划开始容量规划"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建计划</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>资源类型</TableHead>
                      <TableHead>规划周期</TableHead>
                      <TableHead>当前容量</TableHead>
                      <TableHead>预测需求</TableHead>
                      <TableHead>推荐容量</TableHead>
                      <TableHead>置信度</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPlans.map((plan) => (
                      <TableRow key={plan.id}>
                        <TableCell className="font-mono text-sm">{plan.id}</TableCell>
                        <TableCell className="font-medium">{plan.name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getResourceIcon(plan.resource_type)}
                            <span className="capitalize">{plan.resource_type}</span>
                          </div>
                        </TableCell>
                        <TableCell className="capitalize">{plan.planning_horizon}</TableCell>
                        <TableCell>{plan.current_capacity}</TableCell>
                        <TableCell>{plan.projected_demand}</TableCell>
                        <TableCell className="font-medium text-blue-600">{plan.recommended_capacity}</TableCell>
                        <TableCell>{(plan.confidence * 100).toFixed(1)}%</TableCell>
                        <TableCell>
                          <Badge className={plan.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {plan.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(plan.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedPlan(plan)}
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeletePlan(plan.id)}
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

        <TabsContent value="forecasts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                容量预测
              </CardTitle>
            </CardHeader>
            <CardContent>
              {forecastsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !capacityForecasts || capacityForecasts.length === 0 ? (
                <EmptyState title="无预测数据" description="暂无容量预测记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资源类型</TableHead>
                      <TableHead>预测周期</TableHead>
                      <TableHead>模型</TableHead>
                      <TableHead>准确率</TableHead>
                      <TableHead>数据点数</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {capacityForecasts.map((forecast) => (
                      <TableRow key={forecast.id}>
                        <TableCell className="font-mono text-sm">{forecast.id}</TableCell>
                        <TableCell className="capitalize">{forecast.resource_type}</TableCell>
                        <TableCell>{forecast.forecast_period}</TableCell>
                        <TableCell>{forecast.model_used}</TableCell>
                        <TableCell>{(forecast.accuracy * 100).toFixed(1)}%</TableCell>
                        <TableCell>{forecast.predictions.length}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(forecast.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            查看详情
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

        <TabsContent value="optimization" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                优化建议
              </CardTitle>
            </CardHeader>
            <CardContent>
              {optimizationLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !optimizationResults || optimizationResults.length === 0 ? (
                <EmptyState title="无优化建议" description="暂无优化建议记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资源ID</TableHead>
                      <TableHead>资源类型</TableHead>
                      <TableHead>当前利用率</TableHead>
                      <TableHead>潜在节省</TableHead>
                      <TableHead>优化策略</TableHead>
                      <TableHead>工作量</TableHead>
                      <TableHead>影响</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {optimizationResults.map((result) => (
                      <TableRow key={result.id}>
                        <TableCell className="font-mono text-sm">{result.id}</TableCell>
                        <TableCell className="font-mono text-sm">{result.resource_id}</TableCell>
                        <TableCell className="capitalize">{result.resource_type}</TableCell>
                        <TableCell>{(result.current_utilization * 100).toFixed(1)}%</TableCell>
                        <TableCell className="font-medium text-green-600">${result.potential_savings.toFixed(2)}</TableCell>
                        <TableCell>{result.optimization_strategy}</TableCell>
                        <TableCell>
                          <Badge className={getEffortColor(result.effort_level)}>
                            {result.effort_level}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getEffortColor(result.impact_level)}>
                            {result.impact_level}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={result.status === 'implemented' ? 'bg-green-100 text-green-800' : result.status === 'rejected' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}>
                            {result.status}
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

        <TabsContent value="rightsizing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                调整建议
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rightsizingLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !rightsizingRecommendations || rightsizingRecommendations.length === 0 ? (
                <EmptyState title="无调整建议" description="暂无调整建议记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资源ID</TableHead>
                      <TableHead>资源类型</TableHead>
                      <TableHead>当前规格</TableHead>
                      <TableHead>推荐规格</TableHead>
                      <TableHead>操作</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>预计节省</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rightsizingRecommendations.map((rec) => (
                      <TableRow key={rec.id}>
                        <TableCell className="font-mono text-sm">{rec.id}</TableCell>
                        <TableCell className="font-mono text-sm">{rec.resource_id}</TableCell>
                        <TableCell className="capitalize">{rec.resource_type}</TableCell>
                        <TableCell>{rec.current_spec}</TableCell>
                        <TableCell className="font-medium text-blue-600">{rec.recommended_spec}</TableCell>
                        <TableCell>
                          <Badge className={getActionColor(rec.action)}>
                            {rec.action.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getPriorityColor(rec.priority)}>
                            {rec.priority}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium text-green-600">${rec.estimated_savings.toFixed(2)}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(rec.created_at).toLocaleString()}
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
      </Tabs>
    </div>
  );
}
