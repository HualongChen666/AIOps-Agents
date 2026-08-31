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
import { AlertTriangle, Bell, TrendingUp, Settings, RefreshCw, Plus, Trash2, Play, Pause, Zap, Filter, ArrowUpDown } from 'lucide-react';

interface AlertConfig {
  id: string;
  enabled: boolean;
  default_severity: string;
  auto_resolve_timeout: number;
  max_alerts_per_source: number;
  enable_intelligent_analysis: boolean;
  enable_prediction: boolean;
  enable_correlation: boolean;
  retention_days: number;
  notification_cooldown: number;
  escalation_enabled: boolean;
  suppression_enabled: boolean;
}

interface NotificationChannel {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  config: Record<string, any>;
}

interface EscalationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  match_conditions: Record<string, string>[];
  escalation_levels: Record<string, any>[];
  max_escalation_level: number;
}

interface SuppressionRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  match_conditions: Record<string, string>[];
  duration: number;
  reason: string;
}

interface AggregationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  group_by: string[];
  aggregation_type: string;
  window: number;
  threshold: number;
  match_conditions: Record<string, string>[];
}

interface AlertDashboard {
  total_alerts: number;
  open_alerts: number;
  resolved_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  avg_resolution_time: number;
  alerts_by_source: Array<{ source: string; count: number }>;
  alerts_by_severity: Array<{ severity: string; count: number }>;
  trend_data: Array<{ hour: number; count: number }>;
}

export default function AlertsAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'config' | 'channels' | 'escalation' | 'suppression' | 'aggregation'>('dashboard');
  const [selectedRule, setSelectedRule] = useState<any>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch dashboard data
  const { data: dashboardData, isLoading: dashboardLoading, error: dashboardError, refetch: refetchDashboard } = useQuery<AlertDashboard>({
    queryKey: ['alerts-dashboard'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/dashboard?time_range=24h');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  // Fetch alert configuration
  const { data: alertConfig, isLoading: configLoading, error: configError, refetch: refetchConfig } = useQuery<AlertConfig>({
    queryKey: ['alerts-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/configuration');
      return resp.data;
    },
    refetchInterval: 300000,
  });

  // Fetch notification channels
  const { data: notificationChannels, isLoading: channelsLoading, error: channelsError, refetch: refetchChannels } = useQuery<NotificationChannel[]>({
    queryKey: ['notification-channels'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/notification/channels');
      return resp.data.channels || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch escalation rules
  const { data: escalationRules, isLoading: escalationLoading, error: escalationError, refetch: refetchEscalation } = useQuery<EscalationRule[]>({
    queryKey: ['escalation-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/escalation/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch suppression rules
  const { data: suppressionRules, isLoading: suppressionLoading, error: suppressionError, refetch: refetchSuppression } = useQuery<SuppressionRule[]>({
    queryKey: ['suppression-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/suppression/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch aggregation rules
  const { data: aggregationRules, isLoading: aggregationLoading, error: aggregationError, refetch: refetchAggregation } = useQuery<AggregationRule[]>({
    queryKey: ['aggregation-rules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/aggregation/rules');
      return resp.data.rules || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Update configuration mutation
  const updateConfigMutation = useMutation({
    mutationFn: async (config: Partial<AlertConfig>) => {
      const resp = await api.put('/api/v1/alerts/configuration', config);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Configuration updated successfully');
      queryClient.invalidateQueries({ queryKey: ['alerts-config'] });
    },
    onError: (error: any) => {
      showError(`Failed to update configuration: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Toggle rule mutation
  const toggleRuleMutation = useMutation({
    mutationFn: async ({ ruleType, ruleId, enabled }: { ruleType: string; ruleId: string; enabled: boolean }) => {
      const resp = await api.patch(`/api/v1/alerts/${ruleType}/rules/${ruleId}`, { enabled });
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Rule status updated');
      queryClient.invalidateQueries({ queryKey: ['escalation-rules'] });
      queryClient.invalidateQueries({ queryKey: ['suppression-rules'] });
      queryClient.invalidateQueries({ queryKey: ['aggregation-rules'] });
    },
    onError: (error: any) => {
      showError(`Failed to update rule: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete rule mutation
  const deleteRuleMutation = useMutation({
    mutationFn: async ({ ruleType, ruleId }: { ruleType: string; ruleId: string }) => {
      const resp = await api.delete(`/api/v1/alerts/${ruleType}/rules/${ruleId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Rule deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['escalation-rules'] });
      queryClient.invalidateQueries({ queryKey: ['suppression-rules'] });
      queryClient.invalidateQueries({ queryKey: ['aggregation-rules'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete rule: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (dashboardError) {
      setPageError(dashboardError as Error);
      showError('Failed to load dashboard data');
    }
  }, [dashboardError, setPageError, showError]);

  const getStatusColor = (enabled: boolean) => {
    return enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';
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

  const handleToggleRule = (ruleType: string, ruleId: string, currentEnabled: boolean) => {
    toggleRuleMutation.mutate({ ruleType, ruleId, enabled: !currentEnabled });
  };

  const handleDeleteRule = (ruleType: string, ruleId: string) => {
    if (!window.confirm('Are you sure you want to delete this rule?')) return;
    deleteRuleMutation.mutate({ ruleType, ruleId });
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
          description="无法加载告警高级数据，请稍后重试"
          action={<Button onClick={() => refetchDashboard()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchDashboard()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警高级管理</h1>
            <p className="text-sm text-gray-500">告警配置、路由、聚合和智能分析</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchDashboard()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建规则
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="dashboard">
            <TrendingUp className="h-4 w-4 mr-2" />
            仪表盘
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings className="h-4 w-4 mr-2" />
            配置
          </TabsTrigger>
          <TabsTrigger value="channels">
            <Bell className="h-4 w-4 mr-2" />
            通知通道
          </TabsTrigger>
          <TabsTrigger value="escalation">
            <ArrowUpDown className="h-4 w-4 mr-2" />
            升级规则
          </TabsTrigger>
          <TabsTrigger value="suppression">
            <Filter className="h-4 w-4 mr-2" />
            抑制规则
          </TabsTrigger>
          <TabsTrigger value="aggregation">
            <Zap className="h-4 w-4 mr-2" />
            聚合规则
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="space-y-4">
          {dashboardLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : dashboardData ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">总告警数</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-gray-900">{dashboardData.total_alerts}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">未处理告警</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-red-600">{dashboardData.open_alerts}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">已解决告警</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-green-600">{dashboardData.resolved_alerts}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">平均解决时间</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-blue-600">{Math.floor(dashboardData.avg_resolution_time / 60)}m</div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle>告警来源分布</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {dashboardData.alerts_by_source?.map((item) => (
                        <div key={item.source} className="flex items-center justify-between">
                          <span className="text-sm">{item.source}</span>
                          <Badge variant="outline">{item.count}</Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>告警严重度分布</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {dashboardData.alerts_by_severity?.map((item) => (
                        <div key={item.severity} className="flex items-center justify-between">
                          <Badge className={getSeverityColor(item.severity)}>{item.severity}</Badge>
                          <Badge variant="outline">{item.count}</Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : (
            <EmptyState title="无数据" description="暂无仪表盘数据" />
          )}
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                告警配置
              </CardTitle>
            </CardHeader>
            <CardContent>
              {configLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : alertConfig ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">默认严重度</label>
                      <Select
                        value={alertConfig.default_severity}
                        onChange={(e) => updateConfigMutation.mutate({ default_severity: e.target.value })}
                      >
                        <option value="critical">严重</option>
                        <option value="high">高</option>
                        <option value="medium">中</option>
                        <option value="low">低</option>
                      </Select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">自动解决超时(秒)</label>
                      <Input
                        type="number"
                        value={alertConfig.auto_resolve_timeout}
                        onChange={(e) => updateConfigMutation.mutate({ auto_resolve_timeout: parseInt(e.target.value) })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">每个源最大告警数</label>
                      <Input
                        type="number"
                        value={alertConfig.max_alerts_per_source}
                        onChange={(e) => updateConfigMutation.mutate({ max_alerts_per_source: parseInt(e.target.value) })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">保留天数</label>
                      <Input
                        type="number"
                        value={alertConfig.retention_days}
                        onChange={(e) => updateConfigMutation.mutate({ retention_days: parseInt(e.target.value) })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">通知冷却时间(秒)</label>
                      <Input
                        type="number"
                        value={alertConfig.notification_cooldown}
                        onChange={(e) => updateConfigMutation.mutate({ notification_cooldown: parseInt(e.target.value) })}
                      />
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-4">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={alertConfig.enable_intelligent_analysis}
                        onChange={(e) => updateConfigMutation.mutate({ enable_intelligent_analysis: e.target.checked })}
                      />
                      <span className="text-sm">启用智能分析</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={alertConfig.enable_prediction}
                        onChange={(e) => updateConfigMutation.mutate({ enable_prediction: e.target.checked })}
                      />
                      <span className="text-sm">启用预测</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={alertConfig.enable_correlation}
                        onChange={(e) => updateConfigMutation.mutate({ enable_correlation: e.target.checked })}
                      />
                      <span className="text-sm">启用关联分析</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={alertConfig.escalation_enabled}
                        onChange={(e) => updateConfigMutation.mutate({ escalation_enabled: e.target.checked })}
                      />
                      <span className="text-sm">启用升级</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={alertConfig.suppression_enabled}
                        onChange={(e) => updateConfigMutation.mutate({ suppression_enabled: e.target.checked })}
                      />
                      <span className="text-sm">启用抑制</span>
                    </label>
                  </div>
                </div>
              ) : (
                <EmptyState title="无配置" description="暂无告警配置" />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="channels" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                通知通道
              </CardTitle>
            </CardHeader>
            <CardContent>
              {channelsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !notificationChannels || notificationChannels.length === 0 ? (
                <EmptyState title="无通知通道" description="暂无通知通道配置" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {notificationChannels.map((channel) => (
                      <TableRow key={channel.id}>
                        <TableCell className="font-medium">{channel.name}</TableCell>
                        <TableCell>{channel.type}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(channel.enabled)}>
                            {channel.enabled ? '启用' : '禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            编辑
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

        <TabsContent value="escalation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowUpDown className="h-5 w-5" />
                升级规则
              </CardTitle>
            </CardHeader>
            <CardContent>
              {escalationLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !escalationRules || escalationRules.length === 0 ? (
                <EmptyState title="无升级规则" description="暂无升级规则配置" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>最大升级级别</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {escalationRules.map((rule) => (
                      <TableRow key={rule.id}>
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell>{rule.description}</TableCell>
                        <TableCell>{rule.max_escalation_level}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(rule.enabled)}>
                            {rule.enabled ? '启用' : '禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleRule('escalation', rule.id, rule.enabled)}
                            >
                              {rule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteRule('escalation', rule.id)}
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

        <TabsContent value="suppression" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="h-5 w-5" />
                抑制规则
              </CardTitle>
            </CardHeader>
            <CardContent>
              {suppressionLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !suppressionRules || suppressionRules.length === 0 ? (
                <EmptyState title="无抑制规则" description="暂无抑制规则配置" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>持续时间(秒)</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {suppressionRules.map((rule) => (
                      <TableRow key={rule.id}>
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell>{rule.description}</TableCell>
                        <TableCell>{rule.duration}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(rule.enabled)}>
                            {rule.enabled ? '启用' : '禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleRule('suppression', rule.id, rule.enabled)}
                            >
                              {rule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteRule('suppression', rule.id)}
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

        <TabsContent value="aggregation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                聚合规则
              </CardTitle>
            </CardHeader>
            <CardContent>
              {aggregationLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !aggregationRules || aggregationRules.length === 0 ? (
                <EmptyState title="无聚合规则" description="暂无聚合规则配置" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>聚合类型</TableHead>
                      <TableHead>阈值</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {aggregationRules.map((rule) => (
                      <TableRow key={rule.id}>
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell>{rule.description}</TableCell>
                        <TableCell>{rule.aggregation_type}</TableCell>
                        <TableCell>{rule.threshold}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(rule.enabled)}>
                            {rule.enabled ? '启用' : '禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleRule('aggregation', rule.id, rule.enabled)}
                            >
                              {rule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteRule('aggregation', rule.id)}
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
      </Tabs>
    </div>
  );
}
