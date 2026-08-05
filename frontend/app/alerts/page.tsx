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
// 🔧 P1 Integration: Import enhanced hooks and components
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface Alert {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'acknowledged' | 'resolved';
  timestamp: string;
  service: string;
  details?: string;
}

export default function AlertsPage() {
  // 🔧 修复: 使用真实 API 获取告警列表
  const { data: alertsData, isLoading, error, refetch } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts?limit=100');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 10000, // 10秒刷新
  });

  const [alerts, setAlerts] = useState<Alert[]>(alertsData || []);

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(isLoading);

  // 🔧 P1 Integration: Use toast notifications
  const { success: showSuccess, error: showError } = useToast();

  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set());
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filters, setFilters] = useState({
    severity: 'all',
    status: 'all',
    service: '',
    search: '',
  });

  // 🔧 P1 Integration: Use debounce for search
  const debouncedSearch = useDebounce(filters.search, 300);

  // 🔧 修复: 同步 API 数据到本地状态
  useEffect(() => {
    if (alertsData) {
      setAlerts(alertsData);
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
    // 🔧 P1 Integration: Use debounced search
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

  const handleBatchAcknowledge = () => {
    setAlerts(
      alerts.map((alert) =>
        selectedAlerts.has(alert.id) ? { ...alert, status: 'acknowledged' as const } : alert
      )
    );
    setSelectedAlerts(new Set());
    // 🔧 P1 Integration: Show success toast
    showSuccess(`${selectedAlerts.size} alerts acknowledged`);
  };

  const handleBatchResolve = () => {
    setAlerts(
      alerts.map((alert) =>
        selectedAlerts.has(alert.id) ? { ...alert, status: 'resolved' as const } : alert
      )
    );
    setSelectedAlerts(new Set());
    // 🔧 P1 Integration: Show success toast
    showSuccess(`${selectedAlerts.size} alerts resolved`);
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
        <h1 className="text-3xl font-bold text-gray-900">告警管理</h1>
        <div className="flex gap-2">
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

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
                  批量确认
                </Button>
                <Button onClick={handleBatchResolve}>批量解决</Button>
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
              <Button onClick={() => {
                setAlerts(alerts.map(a => a.id === selectedAlert.id ? { ...a, status: 'acknowledged' as const } : a));
                setSelectedAlert(null);
              }}>
                确认
              </Button>
              <Button onClick={() => {
                setAlerts(alerts.map(a => a.id === selectedAlert.id ? { ...a, status: 'resolved' as const } : a));
                setSelectedAlert(null);
              }}>
                解决
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
