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
import { Layout, Settings, RefreshCw, Plus, Trash2, BarChart3, Table as TableIcon, Logs, AlertTriangle, Monitor, Move, Eye, EyeOff, TrendingUp, Activity, CheckCircle, XCircle, Cpu, HardDrive } from 'lucide-react';

interface DashboardWidget {
  id: string;
  widget_type: 'metric' | 'chart' | 'table' | 'log' | 'alert' | 'status';
  title: string;
  description?: string;
  config: Record<string, any>;
  data_source?: string;
  refresh_interval: number;
  position: Record<string, number>;
  size: Record<string, number>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface DashboardLayout {
  id: string;
  name: string;
  layout_type: 'grid' | 'flex' | 'custom';
  widgets: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface StatsSummary {
  alerts: {
    alerts: {
      raw: number;
      effective: number;
    };
    ingestion: {
      total_points: number;
      records: number;
    };
  };
  repairs: {
    total_repairs: number;
    repairs: Array<{
      repair_id: string;
      success: boolean;
      rule_name?: string;
      script_key?: string;
      platform?: string;
      recorded_at: string;
    }>;
  };
  systems: {
    cpu_percent: number;
    memory_percent: number;
    timestamp: string;
  };
  from_cache: boolean;
}

interface RepairRecord {
  repair_id: string;
  success: boolean;
  rule_name?: string;
  script_key?: string;
  platform?: string;
  output?: string;
  recorded_at: string;
}

// Helper functions for stats calculations
function calculateNoiseReduction(raw: number, effective: number): number {
  if (raw === 0) return 0;
  return ((raw - effective) / raw) * 100;
}

function calculateHealRate(repairs: any[]): number {
  if (!repairs || repairs.length === 0) return 0;
  const successful = repairs.filter((r: any) => r.success).length;
  return (successful / repairs.length) * 100;
}

function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString('zh-CN');
}

function getHealthStatus(cpu: number, memory: number): { status: string; color: string } {
  if (cpu > 80 || memory > 80) {
    return { status: '警告', color: 'bg-red-100 text-red-800' };
  }
  if (cpu > 60 || memory > 60) {
    return { status: '注意', color: 'bg-yellow-100 text-yellow-800' };
  }
  return { status: '健康', color: 'bg-green-100 text-green-800' };
}

export default function DashboardAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'widgets' | 'layouts' | 'stats'>('widgets');
  const [selectedWidget, setSelectedWidget] = useState<DashboardWidget | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [newWidgetData, setNewWidgetData] = useState({
    widget_type: 'metric' as const,
    title: '',
    description: '',
    data_source: '',
    refresh_interval: 30,
    enabled: true,
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch dashboard widgets
  const { data: dashboardWidgets, isLoading: widgetsLoading, error: widgetsError, refetch: refetchWidgets } = useQuery<DashboardWidget[]>({
    queryKey: ['dashboard-widgets'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/dashboard/widgets');
      return resp.data.widgets || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch dashboard layouts
  const { data: dashboardLayouts, isLoading: layoutsLoading, error: layoutsError, refetch: refetchLayouts } = useQuery<DashboardLayout[]>({
    queryKey: ['dashboard-layouts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/dashboard/layouts');
      return resp.data.layouts || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch stats summary
  const { data: statsSummary, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useQuery<StatsSummary>({
    queryKey: ['stats-summary'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/stats/summary');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  // Create widget mutation
  const createWidgetMutation = useMutation({
    mutationFn: async (widgetData: typeof newWidgetData) => {
      const resp = await api.post('/api/v1/dashboard/widgets', widgetData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Widget created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['dashboard-widgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to create widget: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete widget mutation
  const deleteWidgetMutation = useMutation({
    mutationFn: async (widgetId: string) => {
      const resp = await api.delete(`/api/v1/dashboard/widgets/${widgetId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Widget deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dashboard-widgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete widget: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Toggle widget mutation
  const toggleWidgetMutation = useMutation({
    mutationFn: async ({ widgetId, enabled }: { widgetId: string; enabled: boolean }) => {
      const resp = await api.patch(`/api/v1/dashboard/widgets/${widgetId}`, { enabled });
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Widget status updated');
      queryClient.invalidateQueries({ queryKey: ['dashboard-widgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to update widget: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (widgetsError) {
      setPageError(widgetsError as Error);
      showError('Failed to load dashboard widgets');
    }
    if (statsError) {
      showError('Failed to load stats data');
    }
  }, [widgetsError, statsError, setPageError, showError]);

  const filteredWidgets = dashboardWidgets?.filter((widget) => {
    if (typeFilter !== 'all' && widget.widget_type !== typeFilter) return false;
    if (debouncedSearch && !widget.title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'metric':
        return <Monitor className="h-4 w-4" />;
      case 'chart':
        return <BarChart3 className="h-4 w-4" />;
      case 'table':
        return <TableIcon className="h-4 w-4" />;
      case 'log':
        return <Logs className="h-4 w-4" />;
      case 'alert':
        return <AlertTriangle className="h-4 w-4" />;
      case 'status':
        return <Monitor className="h-4 w-4" />;
      default:
        return <Layout className="h-4 w-4" />;
    }
  };

  const getLayoutTypeColor = (type: string) => {
    switch (type) {
      case 'grid':
        return 'bg-blue-100 text-blue-800';
      case 'flex':
        return 'bg-green-100 text-green-800';
      case 'custom':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateWidget = () => {
    if (!newWidgetData.title) {
      showError('Please enter widget title');
      return;
    }
    createWidgetMutation.mutate(newWidgetData);
  };

  const handleDeleteWidget = (widgetId: string) => {
    if (!window.confirm('Are you sure you want to delete this widget?')) return;
    deleteWidgetMutation.mutate(widgetId);
  };

  const handleToggleWidget = (widgetId: string, currentEnabled: boolean) => {
    toggleWidgetMutation.mutate({ widgetId, enabled: !currentEnabled });
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
          description="无法加载仪表板数据，请稍后重试"
          action={<Button onClick={() => refetchWidgets()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchWidgets()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layout className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">仪表板高级</h1>
            <p className="text-sm text-gray-500">小部件、布局和仪表板配置管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchWidgets()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建小部件
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="widgets">
            <Monitor className="h-4 w-4 mr-2" />
            小部件
          </TabsTrigger>
          <TabsTrigger value="layouts">
            <Layout className="h-4 w-4 mr-2" />
            布局
          </TabsTrigger>
          <TabsTrigger value="stats">
            <BarChart3 className="h-4 w-4 mr-2" />
            统计数据
          </TabsTrigger>
        </TabsList>

        <TabsContent value="widgets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Monitor className="h-5 w-5" />
                  小部件管理
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索小部件..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                    <option value="all">全部类型</option>
                    <option value="metric">指标</option>
                    <option value="chart">图表</option>
                    <option value="table">表格</option>
                    <option value="log">日志</option>
                    <option value="alert">告警</option>
                    <option value="status">状态</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {widgetsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredWidgets.length === 0 ? (
                <EmptyState
                  title="没有小部件"
                  description="点击创建小部件开始配置仪表板"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建小部件</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>标题</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>数据源</TableHead>
                      <TableHead>刷新间隔</TableHead>
                      <TableHead>位置</TableHead>
                      <TableHead>大小</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建者</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredWidgets.map((widget) => (
                      <TableRow key={widget.id}>
                        <TableCell className="font-mono text-sm">{widget.id}</TableCell>
                        <TableCell className="font-medium">{widget.title}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getTypeIcon(widget.widget_type)}
                            <span className="capitalize">{widget.widget_type}</span>
                          </div>
                        </TableCell>
                        <TableCell>{widget.data_source || '-'}</TableCell>
                        <TableCell>{widget.refresh_interval}s</TableCell>
                        <TableCell>
                          {widget.position.x !== undefined ? `(${widget.position.x}, ${widget.position.y})` : '-'}
                        </TableCell>
                        <TableCell>
                          {widget.size.width !== undefined ? `${widget.size.width}x${widget.size.height}` : '-'}
                        </TableCell>
                        <TableCell>
                          {widget.enabled ? (
                            <Badge className="bg-green-100 text-green-800">启用</Badge>
                          ) : (
                            <Badge className="bg-gray-100 text-gray-800">禁用</Badge>
                          )}
                        </TableCell>
                        <TableCell>{widget.created_by}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(widget.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleWidget(widget.id, widget.enabled)}
                            >
                              {widget.enabled ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedWidget(widget)}
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteWidget(widget.id)}
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

        <TabsContent value="layouts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layout className="h-5 w-5" />
                布局管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              {layoutsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !dashboardLayouts || dashboardLayouts.length === 0 ? (
                <EmptyState title="无布局" description="暂无布局记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>布局类型</TableHead>
                      <TableHead>小部件数</TableHead>
                      <TableHead>默认</TableHead>
                      <TableHead>创建者</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dashboardLayouts.map((layout) => (
                      <TableRow key={layout.id}>
                        <TableCell className="font-mono text-sm">{layout.id}</TableCell>
                        <TableCell className="font-medium">{layout.name}</TableCell>
                        <TableCell>
                          <Badge className={getLayoutTypeColor(layout.layout_type)}>
                            {layout.layout_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{layout.widgets.length}</TableCell>
                        <TableCell>
                          {layout.is_default ? (
                            <Badge className="bg-blue-100 text-blue-800">是</Badge>
                          ) : (
                            <Badge className="bg-gray-100 text-gray-800">否</Badge>
                          )}
                        </TableCell>
                        <TableCell>{layout.created_by}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(layout.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(layout.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Move className="h-4 w-4" />
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

        <TabsContent value="stats" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Alert Stats Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  告警统计
                </CardTitle>
              </CardHeader>
              <CardContent>
                {statsLoading ? (
                  <LoadingSpinner size="sm" />
                ) : statsError ? (
                  <div className="text-red-500 text-sm">加载失败</div>
                ) : statsSummary ? (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">原始告警</span>
                      <span className="text-2xl font-bold">{statsSummary.alerts?.alerts?.raw || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">有效告警</span>
                      <span className="text-2xl font-bold text-blue-600">{statsSummary.alerts?.alerts?.effective || 0}</span>
                    </div>
                    <div className="pt-2 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">降噪效率</span>
                        <span className="text-sm font-semibold text-green-600">
                          {calculateNoiseReduction(
                            statsSummary.alerts?.alerts?.raw || 0,
                            statsSummary.alerts?.alerts?.effective || 0
                          ).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            {/* Repair Stats Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  修复统计
                </CardTitle>
              </CardHeader>
              <CardContent>
                {statsLoading ? (
                  <LoadingSpinner size="sm" />
                ) : statsError ? (
                  <div className="text-red-500 text-sm">加载失败</div>
                ) : statsSummary ? (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">总修复数</span>
                      <span className="text-2xl font-bold">{statsSummary.repairs?.total_repairs || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">成功修复</span>
                      <span className="text-2xl font-bold text-green-600">
                        {statsSummary.repairs?.repairs?.filter((r: any) => r.success).length || 0}
                      </span>
                    </div>
                    <div className="pt-2 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">自愈成功率</span>
                        <span className="text-sm font-semibold text-green-600">
                          {calculateHealRate(statsSummary.repairs?.repairs || []).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            {/* System Stats Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Activity className="h-4 w-4 text-blue-500" />
                  系统状态
                </CardTitle>
              </CardHeader>
              <CardContent>
                {statsLoading ? (
                  <LoadingSpinner size="sm" />
                ) : statsError ? (
                  <div className="text-red-500 text-sm">加载失败</div>
                ) : statsSummary ? (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600 flex items-center gap-1">
                        <Cpu className="h-3 w-3" />
                        CPU
                      </span>
                      <span className="text-2xl font-bold">{(statsSummary.systems?.cpu_percent || 0).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600 flex items-center gap-1">
                        <HardDrive className="h-3 w-3" />
                        内存
                      </span>
                      <span className="text-2xl font-bold">{(statsSummary.systems?.memory_percent || 0).toFixed(1)}%</span>
                    </div>
                    <div className="pt-2 border-t">
                      <Badge className={getHealthStatus(
                        statsSummary.systems?.cpu_percent || 0,
                        statsSummary.systems?.memory_percent || 0
                      ).color}>
                        {getHealthStatus(
                          statsSummary.systems?.cpu_percent || 0,
                          statsSummary.systems?.memory_percent || 0
                        ).status}
                      </Badge>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            {/* Ingestion Stats Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-purple-500" />
                  数据采集
                </CardTitle>
              </CardHeader>
              <CardContent>
                {statsLoading ? (
                  <LoadingSpinner size="sm" />
                ) : statsError ? (
                  <div className="text-red-500 text-sm">加载失败</div>
                ) : statsSummary ? (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">数据点总数</span>
                      <span className="text-2xl font-bold">{statsSummary.alerts?.ingestion?.total_points || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">采集记录数</span>
                      <span className="text-2xl font-bold text-purple-600">{statsSummary.alerts?.ingestion?.records || 0}</span>
                    </div>
                    <div className="pt-2 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">平均点数/记录</span>
                        <span className="text-sm font-semibold">
                          {statsSummary.alerts?.ingestion?.records > 0
                            ? (statsSummary.alerts.ingestion.total_points / statsSummary.alerts.ingestion.records).toFixed(1)
                            : '0'}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>

          {/* Repair History Table */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Logs className="h-5 w-5" />
                  修复记录历史
                </span>
                <Button onClick={() => refetchStats()} variant="outline" size="sm">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  刷新
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : statsError ? (
                <EmptyState
                  title="加载失败"
                  description="无法加载修复记录，请稍后重试"
                  action={<Button onClick={() => refetchStats()}>重试</Button>}
                />
              ) : !statsSummary?.repairs?.repairs || statsSummary.repairs.repairs.length === 0 ? (
                <EmptyState
                  title="暂无修复记录"
                  description="系统暂无修复操作记录"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>修复ID</TableHead>
                      <TableHead>规则名称</TableHead>
                      <TableHead>脚本Key</TableHead>
                      <TableHead>平台</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>记录时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {statsSummary.repairs.repairs.slice(0, 20).map((repair: RepairRecord) => (
                      <TableRow key={repair.repair_id}>
                        <TableCell className="font-mono text-sm">{repair.repair_id.slice(0, 8)}...</TableCell>
                        <TableCell>{repair.rule_name || '-'}</TableCell>
                        <TableCell>{repair.script_key || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{repair.platform || 'unknown'}</Badge>
                        </TableCell>
                        <TableCell>
                          {repair.success ? (
                            <Badge className="bg-green-100 text-green-800 flex items-center gap-1">
                              <CheckCircle className="h-3 w-3" />
                              成功
                            </Badge>
                          ) : (
                            <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
                              <XCircle className="h-3 w-3" />
                              失败
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {formatTimestamp(repair.recorded_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Stats Info Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">统计信息</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">数据来源</span>
                  <span className="font-medium">后端统计引擎</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">缓存状态</span>
                  <span className="font-medium">
                    {statsSummary?.from_cache ? (
                      <Badge className="bg-blue-100 text-blue-800">已缓存</Badge>
                    ) : (
                      <Badge className="bg-gray-100 text-gray-800">实时</Badge>
                    )}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">刷新间隔</span>
                  <span className="font-medium">30秒</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">API端点</span>
                  <span className="font-mono text-xs">/api/v1/stats/summary</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建小部件</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
              <Input
                value={newWidgetData.title}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, title: e.target.value })}
                placeholder="输入小部件标题"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={newWidgetData.description}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, description: e.target.value })}
                placeholder="小部件描述"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
              <Select
                value={newWidgetData.widget_type}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, widget_type: e.target.value as any })}
              >
                <option value="metric">指标</option>
                <option value="chart">图表</option>
                <option value="table">表格</option>
                <option value="log">日志</option>
                <option value="alert">告警</option>
                <option value="status">状态</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">数据源</label>
              <Input
                value={newWidgetData.data_source}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, data_source: e.target.value })}
                placeholder="数据源URL或API端点"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">刷新间隔(秒)</label>
              <Input
                type="number"
                value={newWidgetData.refresh_interval}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, refresh_interval: parseInt(e.target.value) })}
                placeholder="刷新间隔"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={newWidgetData.enabled}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, enabled: e.target.checked })}
              />
              <span className="text-sm">启用小部件</span>
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateWidget} disabled={createWidgetMutation.isPending}>
              {createWidgetMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
