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
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { useRealtimeData } from '@/hooks/useWebSocket';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { AlertTriangle, Bell, TrendingUp, Brain, Trash2, CheckCircle, XCircle, Wifi, WifiOff } from 'lucide-react';

interface Alert {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'acknowledged' | 'resolved';
  timestamp: string;
  service: string;
  details?: string;
}

interface IntelligenceStats {
  total_patterns: number;
  noise_patterns: number;
  cluster_count: number;
  last_updated: string;
}

interface AlertPattern {
  pattern_id: string;
  signature: string;
  frequency: number;
  last_seen: string;
  is_noise: boolean;
  noise_reason?: string;
}

export default function AlertsPage() {
  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set());
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filters, setFilters] = useState({
    severity: 'all',
    status: 'all',
    service: '',
    search: '',
  });
  const [activeTab, setActiveTab] = useState<'alerts' | 'intelligence' | 'patterns'>('alerts');

  // 🔧 修复: 使用真实 API 获取告警列表
  const { data: alertsData, isLoading, error, refetch } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/?limit=100');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 10000, // 10秒刷新
  });

  const [alerts, setAlerts] = useState<Alert[]>([]);

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(isLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Use debounce for search
  const debouncedSearch = useDebounce(filters.search, 300);

  // 🔧 智能告警统计
  const { data: intelligenceStats } = useQuery<IntelligenceStats>({
    queryKey: ['alert-intelligence-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/intelligence/statistics');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 告警模式
  const { data: alertPatterns } = useQuery<{ patterns: AlertPattern[]; total: number }>({
    queryKey: ['alert-patterns'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/intelligence/patterns?limit=50');
      return resp.data;
    },
    refetchInterval: 120000, // 120秒刷新
  });

  // 🔧 Week 7: 实时数据优化 - SSE实时告警推送
  const { isConnected: sseConnected, data: realtimeAlert } = useRealtimeData<Alert>('/api/v1/sse/events', {
    enabled: true,
    reconnectInterval: 5000,
    maxReconnectAttempts: 5,
    onEvent: (event) => {
      if (event.type === 'alert' && event.data) {
        const newAlert = normalizeAlert(event.data, alerts.length);
        setAlerts((prev) => [newAlert, ...prev]);
      }
    },
  });

  // 🔧 修复: 同步 API 数据到本地状态并规范化字段
  const normalizeAlert = (a: any, index: number): Alert => {
    const severityMap: Record<string, string> = {
      fatal: 'critical',
      critical: 'critical',
      warning: 'high',
      info: 'low',
    };
    const rawSeverity = a.severity || a.level || 'medium';
    const severity = (severityMap[rawSeverity] || rawSeverity) as Alert['severity'];
    const rawStatus = a.status || 'open';
    const status = (['open', 'acknowledged', 'resolved'].includes(rawStatus) ? rawStatus : 'open') as Alert['status'];
    return {
      id: a.id || a.trace_id || `alert-${index}`,
      title: a.title || a.desc || a.message || '未知告警',
      severity,
      status,
      timestamp: a.timestamp || a.detected_at || a.metric_time || a.raw_time || new Date().toISOString(),
      service: a.service || a.host || a.metric || 'unknown',
      details: a.details || a.desc || a.message || '',
    };
  };

  useEffect(() => {
    if (alertsData) {
      const raw = Array.isArray(alertsData) ? alertsData : (alertsData as any).alerts || [];
      setAlerts(raw.map(normalizeAlert));
    }
  }, [alertsData]);

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (error) {
      showError('Failed to load alerts');
      setPageError(error as Error);
    }
  }, [error, showError, setPageError]);

  const filteredAlerts = alerts.filter((alert) => {
    if (filters.severity !== 'all' && alert.severity !== filters.severity) return false;
    if (filters.status !== 'all' && alert.status !== filters.status) return false;
    if (filters.service && !alert.service.includes(filters.service)) return false;
    if (debouncedSearch && !alert.title.includes(debouncedSearch)) return false;
    return true;
  });

  const handleSelectAll = () => {
    if (selectedAlerts.size === filteredAlerts.length) {
      setSelectedAlerts(new Set());
    } else {
      setSelectedAlerts(new Set(filteredAlerts.map((a) => a.id)));
    }
  };

  const handleSelectAlert = (id: string) => {
    const newSelected = new Set(selectedAlerts);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedAlerts(newSelected);
  };

  const handleBatchAcknowledge = async () => {
    const ids = Array.from(selectedAlerts);
    if (ids.length === 0) return;
    await Promise.all(ids.map((id) => api.post(`/api/v1/alerts/${id}/acknowledge`)));
    setSelectedAlerts(new Set());
    showSuccess(`${ids.length} alerts acknowledged`);
    await refetch();
  };

  const handleBatchResolve = async () => {
    const ids = Array.from(selectedAlerts);
    if (ids.length === 0) return;
    await Promise.all(ids.map((id) => api.post(`/api/v1/alerts/${id}/resolve`)));
    setSelectedAlerts(new Set());
    showSuccess(`${ids.length} alerts resolved`);
    await refetch();
  };

  const handleAcknowledge = async (id: string) => {
    await api.post(`/api/v1/alerts/${id}/acknowledge`);
    setSelectedAlert(null);
    await refetch();
  };

  const handleResolve = async (id: string) => {
    await api.post(`/api/v1/alerts/${id}/resolve`);
    setSelectedAlert(null);
    await refetch();
  };

  const handleClearAlerts = async () => {
    if (!window.confirm('确定要清空所有告警历史吗？此操作不可恢复。')) return;
    try {
      await api.delete('/api/v1/alerts/');
      showSuccess('告警历史已清空');
      await refetch();
    } catch (error) {
      showError('清空告警失败');
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
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-red-100 text-red-800';
      case 'acknowledged':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'alerts' as const, label: '告警列表', icon: Bell },
    { key: 'intelligence' as const, label: '智能分析', icon: Brain },
    { key: 'patterns' as const, label: '告警模式', icon: TrendingUp },
  ];

  // 🔧 P1 Integration: Use enhanced loading and empty states
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
          description="无法加载告警数据，请稍后重试"
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetch()}>重试</Button>}
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
            <h1 className="text-3xl font-bold text-gray-900">告警管理</h1>
            <p className="text-sm text-gray-500">实时监控和管理系统告警</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-sm">
            {sseConnected ? (
              <>
                <Wifi className="h-4 w-4 text-green-500" />
                <span className="text-green-600">实时连接</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-gray-400" />
                <span className="text-gray-500">离线</span>
              </>
            )}
          </div>
          <Button onClick={() => refetch()} variant="outline">
            刷新
          </Button>
          <Button onClick={handleClearAlerts} variant="destructive">
            <Trash2 className="h-4 w-4 mr-2" />
            清空历史
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-[var(--accent-blue)] text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {activeTab === 'alerts' && (
        <>
          {/* 筛选器 */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                    value={filters.status}
                    onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  >
                    <option value="all">全部</option>
                    <option value="open">未处理</option>
                    <option value="acknowledged">已确认</option>
                    <option value="resolved">已解决</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
                  <Input
                    value={filters.service}
                    onChange={(e) => setFilters({ ...filters, service: e.target.value })}
                    placeholder="输入服务名称"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
                  <Input
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    placeholder="搜索告警标题"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 批量操作 */}
          {selectedAlerts.size > 0 && (
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    已选择 {selectedAlerts.size} 个告警
                  </span>
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={handleBatchAcknowledge}>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      批量确认
                    </Button>
                    <Button onClick={handleBatchResolve}>
                      <XCircle className="h-4 w-4 mr-2" />
                      批量解决
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 告警列表 */}
          <Card>
            <CardHeader>
              <CardTitle>告警列表 ({filteredAlerts.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <input
                        type="checkbox"
                        checked={selectedAlerts.size === filteredAlerts.length && filteredAlerts.length > 0}
                        onChange={handleSelectAll}
                      />
                    </TableHead>
                    <TableHead>ID</TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead>严重度</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>时间</TableHead>
                    <TableHead>服务</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAlerts.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8}>
                        <EmptyState
                          title="没有告警"
                          description="当前没有符合条件的告警"
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredAlerts.map((alert) => (
                      <TableRow key={alert.id} className="cursor-pointer hover:bg-gray-50">
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selectedAlerts.has(alert.id)}
                            onChange={() => handleSelectAlert(alert.id)}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-sm">{alert.id}</TableCell>
                        <TableCell className="font-medium">{alert.title}</TableCell>
                        <TableCell>
                          <Badge className={getSeverityColor(alert.severity)}>
                            {alert.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(alert.status)}>
                            {alert.status === 'open' ? '未处理' : alert.status === 'acknowledged' ? '已确认' : '已解决'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(alert.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>{alert.service}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedAlert(alert)}
                          >
                            查看详情
                          </Button>
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

      {activeTab === 'intelligence' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              智能告警统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            {intelligenceStats ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">总模式数</div>
                  <div className="text-2xl font-bold text-[var(--accent-blue)]">{intelligenceStats.total_patterns}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">噪声模式</div>
                  <div className="text-2xl font-bold text-[var(--accent-yellow)]">{intelligenceStats.noise_patterns}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">集群数量</div>
                  <div className="text-2xl font-bold text-[var(--accent-green)]">{intelligenceStats.cluster_count}</div>
                </div>
                <div className="col-span-3 text-sm text-gray-500">
                  最后更新: {new Date(intelligenceStats.last_updated).toLocaleString()}
                </div>
              </div>
            ) : (
              <EmptyState
                title="智能告警引擎不可用"
                description="智能告警功能当前不可用"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'patterns' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              告警模式分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alertPatterns && alertPatterns.patterns && alertPatterns.patterns.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>模式ID</TableHead>
                    <TableHead>签名</TableHead>
                    <TableHead>频率</TableHead>
                    <TableHead>最后出现</TableHead>
                    <TableHead>噪声</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alertPatterns.patterns.map((pattern) => (
                    <TableRow key={pattern.pattern_id}>
                      <TableCell className="font-mono text-sm">{pattern.pattern_id}</TableCell>
                      <TableCell>{pattern.signature}</TableCell>
                      <TableCell>{pattern.frequency}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(pattern.last_seen).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {pattern.is_noise ? (
                          <Badge variant="destructive">是 - {pattern.noise_reason}</Badge>
                        ) : (
                          <Badge variant="default">否</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState
                title="暂无告警模式"
                description="当前没有可用的告警模式数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* 告警详情弹窗 */}
      {selectedAlert && (
        <Dialog open={!!selectedAlert} onOpenChange={() => setSelectedAlert(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>告警详情 - {selectedAlert.id}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">标题</label>
                <p className="mt-1 text-sm text-gray-900">{selectedAlert.title}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">严重度</label>
                <Badge className={getSeverityColor(selectedAlert.severity)}>
                  {selectedAlert.severity}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">状态</label>
                <Badge className={getStatusColor(selectedAlert.status)}>
                  {selectedAlert.status}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">服务</label>
                <p className="mt-1 text-sm text-gray-900">{selectedAlert.service}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">时间</label>
                <p className="mt-1 text-sm text-gray-900">
                  {new Date(selectedAlert.timestamp).toLocaleString()}
                </p>
              </div>
              {selectedAlert.details && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">详情</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedAlert.details}</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedAlert(null)}>
                关闭
              </Button>
              <Button onClick={() => selectedAlert && handleAcknowledge(selectedAlert.id)}>
                <CheckCircle className="h-4 w-4 mr-2" />
                确认
              </Button>
              <Button onClick={() => selectedAlert && handleResolve(selectedAlert.id)}>
                <XCircle className="h-4 w-4 mr-2" />
                解决
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}