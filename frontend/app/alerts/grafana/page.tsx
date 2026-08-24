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
import { BarChart3, AlertTriangle, CheckCircle, XCircle, RefreshCw, Settings, Link } from 'lucide-react';

interface GrafanaAlert {
  id: string;
  title: string;
  state: 'alerting' | 'pending' | 'ok' | 'no_data';
  severity: 'critical' | 'warning' | 'info';
  dashboardId: number;
  dashboardUid: string;
  dashboardSlug: string;
  panelId: number;
  url: string;
  condition: string;
  evalMatches?: Array<{
    metric: string;
    value: number;
  }>;
  alerts: Array<{
    state: string;
    time: string;
  }>;
  executionError?: string;
}

interface GrafanaConfig {
  url: string;
  apiKey: string;
  enabled: boolean;
}

export default function GrafanaAlertsPage() {
  const [selectedAlert, setSelectedAlert] = useState<GrafanaAlert | null>(null);
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

  // 获取Grafana告警列表
  const { data: alertsData, isLoading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useQuery<GrafanaAlert[]>({
    queryKey: ['grafana-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/grafana');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 获取Grafana配置
  const { data: configData, refetch: refetchConfig } = useQuery<GrafanaConfig>({
    queryKey: ['grafana-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/grafana/config');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  const [config, setConfig] = useState<GrafanaConfig>({
    url: '',
    apiKey: '',
    enabled: false,
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (alertsError) {
      showError('Failed to load Grafana alerts');
    }
  }, [alertsError, showError]);

  const filteredAlerts = (alertsData || []).filter((alert) => {
    if (filters.severity !== 'all' && alert.severity !== filters.severity) return false;
    if (filters.state !== 'all' && alert.state !== filters.state) return false;
    if (debouncedSearch && !alert.title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleSaveConfig = async () => {
    try {
      await api.put('/api/v1/alerts/grafana/config', config);
      showSuccess('配置已保存');
      setShowConfig(false);
      await refetchConfig();
    } catch (error) {
      showError('保存配置失败');
    }
  };

  const handleSyncAlerts = async () => {
    try {
      await api.post('/api/v1/alerts/grafana/sync');
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
      case 'alerting':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'ok':
        return 'bg-green-100 text-green-800';
      case 'no_data':
        return 'bg-gray-100 text-gray-800';
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
          <BarChart3 className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Grafana告警</h1>
            <p className="text-sm text-gray-500">管理和监控Grafana告警</p>
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
              Grafana配置状态
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                <div className="text-sm text-gray-500 mb-1">API密钥</div>
                <div className="text-sm font-mono">{configData.apiKey ? '••••••••' : '未配置'}</div>
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
                <option value="alerting">告警中</option>
                <option value="pending">待处理</option>
                <option value="ok">正常</option>
                <option value="no_data">无数据</option>
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

      {/* 告警列表 */}
      <Card>
        <CardHeader>
          <CardTitle>告警列表 ({filteredAlerts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>标题</TableHead>
                <TableHead>严重度</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>仪表盘</TableHead>
                <TableHead>面板ID</TableHead>
                <TableHead>条件</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAlerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState
                      title="没有告警"
                      description="当前没有符合条件的Grafana告警"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAlerts.map((alert) => (
                  <TableRow key={alert.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{alert.title}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(alert.severity)}>
                        {alert.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStateColor(alert.state)}>
                        {alert.state === 'alerting' ? '告警中' : alert.state === 'pending' ? '待处理' : alert.state === 'ok' ? '正常' : '无数据'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{alert.dashboardSlug}</TableCell>
                    <TableCell className="font-mono text-sm">{alert.panelId}</TableCell>
                    <TableCell className="text-sm text-gray-500 truncate max-w-xs">{alert.condition}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedAlert(alert)}
                        >
                          详情
                        </Button>
                        {alert.url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(alert.url, '_blank')}
                          >
                            <Link className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
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
                  <Badge className={getStateColor(selectedAlert.state)}>
                    {selectedAlert.state}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">条件</label>
                <div className="text-sm bg-gray-100 p-2 rounded">{selectedAlert.condition}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">仪表盘ID</label>
                  <div className="text-sm font-mono">{selectedAlert.dashboardId}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">面板ID</label>
                  <div className="text-sm font-mono">{selectedAlert.panelId}</div>
                </div>
              </div>
              {selectedAlert.evalMatches && selectedAlert.evalMatches.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">评估匹配</label>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>指标</TableHead>
                        <TableHead>值</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedAlert.evalMatches.map((match, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-sm">{match.metric}</TableCell>
                          <TableCell className="font-mono text-sm">{match.value}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {selectedAlert.executionError && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">执行错误</label>
                  <div className="text-sm bg-red-50 p-2 rounded text-red-600">{selectedAlert.executionError}</div>
                </div>
              )}
              {selectedAlert.url && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Grafana链接</label>
                  <a href={selectedAlert.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline flex items-center gap-1">
                    <Link className="h-4 w-4" />
                    {selectedAlert.url}
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
            <DialogTitle>Grafana配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Grafana URL</label>
              <Input
                value={config.url}
                onChange={(e) => setConfig({ ...config, url: e.target.value })}
                placeholder="http://grafana:3000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API密钥</label>
              <Input
                type="password"
                value={config.apiKey}
                onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                placeholder="输入API密钥"
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
