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
import { Activity, AlertTriangle, CheckCircle, XCircle, RefreshCw, Settings } from 'lucide-react';

interface PrometheusAlert {
  id: string;
  name: string;
  severity: 'critical' | 'warning' | 'info';
  state: 'firing' | 'pending' | 'resolved';
  value: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  startsAt: string;
  endsAt?: string;
  generatorURL: string;
  fingerprint: string;
}

interface PrometheusConfig {
  url: string;
  enabled: boolean;
  scrape_interval: string;
  evaluation_interval: string;
}

export default function PrometheusAlertsPage() {
  const [selectedAlert, setSelectedAlert] = useState<PrometheusAlert | null>(null);
  const [filters, setFilters] = useState({
    severity: 'all',
    state: 'all',
    search: '',
  });
  const [showConfig, setShowConfig] = useState(false);

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 获取Prometheus告警列表
  const { data: alertsData, isLoading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useQuery<PrometheusAlert[]>({
    queryKey: ['prometheus-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/prometheus');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 获取Prometheus配置
  const { data: configData, refetch: refetchConfig } = useQuery<PrometheusConfig>({
    queryKey: ['prometheus-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/prometheus/config');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  const [config, setConfig] = useState<PrometheusConfig>({
    url: '',
    enabled: false,
    scrape_interval: '15s',
    evaluation_interval: '15s',
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (alertsError) {
      showError('Failed to load Prometheus alerts');
    }
  }, [alertsError, showError]);

  const filteredAlerts = (alertsData || []).filter((alert) => {
    if (filters.severity !== 'all' && alert.severity !== filters.severity) return false;
    if (filters.state !== 'all' && alert.state !== filters.state) return false;
    if (debouncedSearch && !alert.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleSaveConfig = async () => {
    try {
      await api.put('/api/v1/alerts/prometheus/config', config);
      showSuccess('配置已保存');
      setShowConfig(false);
      await refetchConfig();
    } catch (error) {
      showError('保存配置失败');
    }
  };

  const handleSyncAlerts = async () => {
    try {
      await api.post('/api/v1/alerts/prometheus/sync');
      showSuccess('告警同步成功');
      await refetchAlerts();
    } catch (error) {
      showError('同步告警失败');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-orange-100 text-orange-800';
      case 'info':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'firing':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (alertsLoading) {
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
          <Activity className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Prometheus告警</h1>
            <p className="text-sm text-gray-500">管理和监控Prometheus告警</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowConfig(true)} variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            配置
          </Button>
          <Button onClick={handleSyncAlerts} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            同步告警
          </Button>
          <Button onClick={() => refetchAlerts()}>
            刷新
          </Button>
        </div>
      </div>

      {/* 配置状态卡片 */}
      {configData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Prometheus配置状态
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">状态</div>
                <Badge className={configData.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                  {configData.enabled ? '已启用' : '已禁用'}
                </Badge>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">URL</div>
                <div className="text-sm font-mono">{configData.url || '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">采集间隔</div>
                <div className="text-sm font-mono">{configData.scrape_interval}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">评估间隔</div>
                <div className="text-sm font-mono">{configData.evaluation_interval}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">严重度</label>
              <Select
                value={filters.severity}
                onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="critical">严重</option>
                <option value="warning">警告</option>
                <option value="info">信息</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <Select
                value={filters.state}
                onChange={(e) => setFilters({ ...filters, state: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="firing">触发中</option>
                <option value="pending">待处理</option>
                <option value="resolved">已解决</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <Input
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="搜索告警名称"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 告警列表 */}
      <Card>
        <CardHeader>
          <CardTitle>告警列表 ({filteredAlerts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>严重度</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>值</TableHead>
                <TableHead>标签</TableHead>
                <TableHead>开始时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAlerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState
                      title="没有告警"
                      description="当前没有符合条件的Prometheus告警"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAlerts.map((alert) => (
                  <TableRow key={alert.fingerprint} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{alert.name}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(alert.severity)}>
                        {alert.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStateColor(alert.state)}>
                        {alert.state === 'firing' ? '触发中' : alert.state === 'pending' ? '待处理' : '已解决'}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{alert.value}</TableCell>
                    <TableCell className="text-sm">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(alert.labels).slice(0, 3).map(([key, value]) => (
                          <Badge key={key} variant="outline" className="text-xs">
                            {key}={value}
                          </Badge>
                        ))}
                        {Object.keys(alert.labels).length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{Object.keys(alert.labels).length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(alert.startsAt).toLocaleString()}
                    </TableCell>
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

      {/* 告警详情对话框 */}
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
                <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
                <div className="text-lg font-semibold">{selectedAlert.name}</div>
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
                  <Badge className={getStateColor(selectedAlert.state)}>
                    {selectedAlert.state}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">当前值</label>
                <div className="font-mono text-sm bg-gray-100 p-2 rounded">{selectedAlert.value}</div>
              </div>
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">注解</label>
                <div className="space-y-2">
                  {Object.entries(selectedAlert.annotations).map(([key, value]) => (
                    <div key={key} className="text-sm bg-gray-100 p-2 rounded">
                      <span className="font-medium">{key}:</span> {value}
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">开始时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAlert.startsAt).toLocaleString()}</div>
                </div>
                {selectedAlert.endsAt && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">结束时间</label>
                    <div className="text-sm text-gray-600">{new Date(selectedAlert.endsAt).toLocaleString()}</div>
                  </div>
                )}
              </div>
              {selectedAlert.generatorURL && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">生成器URL</label>
                  <a href={selectedAlert.generatorURL} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    {selectedAlert.generatorURL}
                  </a>
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

      {/* 配置对话框 */}
      <Dialog open={showConfig} onOpenChange={setShowConfig}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Prometheus配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prometheus URL</label>
              <Input
                value={config.url}
                onChange={(e) => setConfig({ ...config, url: e.target.value })}
                placeholder="http://prometheus:9090"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">启用</label>
              <Select
                value={config.enabled ? 'true' : 'false'}
                onChange={(e) => setConfig({ ...config, enabled: e.target.value === 'true' })}
              >
                <option value="true">是</option>
                <option value="false">否</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">采集间隔</label>
              <Input
                value={config.scrape_interval}
                onChange={(e) => setConfig({ ...config, scrape_interval: e.target.value })}
                placeholder="15s"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">评估间隔</label>
              <Input
                value={config.evaluation_interval}
                onChange={(e) => setConfig({ ...config, evaluation_interval: e.target.value })}
                placeholder="15s"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfig(false)}>
              取消
            </Button>
            <Button onClick={handleSaveConfig}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
