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
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { History, AlertTriangle, CheckCircle, XCircle, RefreshCw, Calendar } from 'lucide-react';

interface AlertHistory {
  id: string;
  alert_id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'acknowledged' | 'resolved';
  source: string;
  service: string;
  labels: Record<string, string>;
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  acknowledged_by?: string;
  resolved_by?: string;
  duration?: number;
}

export default function AlertHistoryPage() {
  const [selectedAlert, setSelectedAlert] = useState<AlertHistory | null>(null);
  const [filters, setFilters] = useState({
    severity: 'all',
    status: 'all',
    source: '',
    dateRange: '7d',
    search: '',
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const { data: historyData, isLoading: historyLoading, error: historyError, refetch: refetchHistory } = useQuery<AlertHistory[]>({
    queryKey: ['alert-history', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.severity !== 'all') params.append('severity', filters.severity);
      if (filters.status !== 'all') params.append('status', filters.status);
      if (filters.source) params.append('source', filters.source);
      if (filters.dateRange) params.append('date_range', filters.dateRange);
      const resp = await api.get(`/api/v1/alerts/history?${params.toString()}`);
      return resp.data.history || resp.data || [];
    },
    refetchInterval: 30000,
  });

  useEffect(() => {
    if (historyError) showError('Failed to load alert history');
  }, [historyError, showError]);

  const filteredHistory = (historyData || []).filter((alert) => {
    if (debouncedSearch && !alert.title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.severity !== 'all') params.append('severity', filters.severity);
      if (filters.status !== 'all') params.append('status', filters.status);
      if (filters.source) params.append('source', filters.source);
      if (filters.dateRange) params.append('date_range', filters.dateRange);
      
      const resp = await api.get(`/api/v1/alerts/history/export?${params.toString()}`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `alert-history-${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showSuccess('导出成功');
    } catch (error) {
      showError('导出失败');
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

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  if (historyLoading) {
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
          <History className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警历史</h1>
            <p className="text-sm text-gray-500">查看历史告警记录和处理情况</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleExport} variant="outline">
            <Calendar className="h-4 w-4 mr-2" />
            导出
          </Button>
          <Button onClick={() => refetchHistory()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
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
              <label className="block text-sm font-medium text-gray-700 mb-1">来源</label>
              <Input
                value={filters.source}
                onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                placeholder="输入来源"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">时间范围</label>
              <Select
                value={filters.dateRange}
                onChange={(e) => setFilters({ ...filters, dateRange: e.target.value })}
              >
                <option value="1h">最近1小时</option>
                <option value="24h">最近24小时</option>
                <option value="7d">最近7天</option>
                <option value="30d">最近30天</option>
                <option value="90d">最近90天</option>
              </Select>
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

      <Card>
        <CardHeader>
          <CardTitle>告警历史 ({filteredHistory.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>严重度</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>来源</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>持续时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredHistory.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9}>
                    <EmptyState
                      title="没有历史记录"
                      description="当前没有符合条件的告警历史"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredHistory.map((alert) => (
                  <TableRow key={alert.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-mono text-sm">{alert.alert_id}</TableCell>
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
                    <TableCell className="text-sm">{alert.source}</TableCell>
                    <TableCell className="text-sm">{alert.service}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(alert.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm">{formatDuration(alert.duration)}</TableCell>
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

      <Dialog open={!!selectedAlert} onOpenChange={() => setSelectedAlert(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              告警详情
            </DialogTitle>
          </DialogHeader>
          {selectedAlert && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警ID</label>
                <div className="text-lg font-semibold font-mono">{selectedAlert.alert_id}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                <div className="text-lg font-semibold">{selectedAlert.title}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">严重度</label>
                  <Badge className={getSeverityColor(selectedAlert.severity)}>
                    {selectedAlert.severity}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={getStatusColor(selectedAlert.status)}>
                    {selectedAlert.status}
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">来源</label>
                  <div className="text-sm">{selectedAlert.source}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
                  <div className="text-sm">{selectedAlert.service}</div>
                </div>
              </div>
              {selectedAlert.labels && Object.keys(selectedAlert.labels).length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">标签</label>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(selectedAlert.labels).map(([key, value]) => (
                      <Badge key={key} variant="outline">
                        {key}={value}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">创建时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAlert.created_at).toLocaleString()}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">持续时间</label>
                  <div className="text-sm text-gray-600">{formatDuration(selectedAlert.duration)}</div>
                </div>
              </div>
              {selectedAlert.acknowledged_at && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">确认时间</label>
                    <div className="text-sm text-gray-600">{new Date(selectedAlert.acknowledged_at).toLocaleString()}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">确认人</label>
                    <div className="text-sm">{selectedAlert.acknowledged_by}</div>
                  </div>
                </div>
              )}
              {selectedAlert.resolved_at && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">解决时间</label>
                    <div className="text-sm text-gray-600">{new Date(selectedAlert.resolved_at).toLocaleString()}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">解决人</label>
                    <div className="text-sm">{selectedAlert.resolved_by}</div>
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedAlert(null)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
