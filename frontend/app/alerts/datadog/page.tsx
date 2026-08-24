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
import { Dog, AlertTriangle, CheckCircle, XCircle, RefreshCw, Settings, Link } from 'lucide-react';

interface DatadogAlert {
  id: string;
  name: string;
  type: string;
  query: string;
  message: string;
  status: 'triggered' | 'recovered' | 'no_data';
  priority: 'P1' | 'P2' | 'P3' | 'P4' | 'P5';
  created: string;
  modified: string;
  creator: string;
  org_id: number;
  is_deleted: boolean;
  multi: boolean;
  notify_no_data: boolean;
  renotify_interval: number;
  timeout_h: number;
  silenced: boolean;
  dashboard_id?: number;
}

interface DatadogConfig {
  apiKey: string;
  appKey: string;
  site: string;
  enabled: boolean;
}

export default function DatadogAlertsPage() {
  const [selectedAlert, setSelectedAlert] = useState<DatadogAlert | null>(null);
  const [filters, setFilters] = useState({
    priority: 'all',
    status: 'all',
    search: '',
  });
  const [showConfig, setShowConfig] = useState(false);

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 获取Datadog告警列表
  const { data: alertsData, isLoading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useQuery<DatadogAlert[]>({
    queryKey: ['datadog-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/datadog');
      return resp.data.alerts || resp.data || [];
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 获取Datadog配置
  const { data: configData, refetch: refetchConfig } = useQuery<DatadogConfig>({
    queryKey: ['datadog-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/datadog/config');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  const [config, setConfig] = useState<DatadogConfig>({
    apiKey: '',
    appKey: '',
    site: 'datadoghq.com',
    enabled: false,
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (alertsError) {
      showError('Failed to load Datadog alerts');
    }
  }, [alertsError, showError]);

  const filteredAlerts = (alertsData || []).filter((alert) => {
    if (filters.priority !== 'all' && alert.priority !== filters.priority) return false;
    if (filters.status !== 'all' && alert.status !== filters.status) return false;
    if (debouncedSearch && !alert.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleSaveConfig = async () => {
    try {
      await api.put('/api/v1/alerts/datadog/config', config);
      showSuccess('配置已保存');
      setShowConfig(false);
      await refetchConfig();
    } catch (error) {
      showError('保存配置失败');
    }
  };

  const handleSyncAlerts = async () => {
    try {
      await api.post('/api/v1/alerts/datadog/sync');
      showSuccess('告警同步成功');
      await refetchAlerts();
    } catch (error) {
      showError('同步告警失败');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P1':
        return 'bg-red-100 text-red-800';
      case 'P2':
        return 'bg-orange-100 text-orange-800';
      case 'P3':
        return 'bg-yellow-100 text-yellow-800';
      case 'P4':
        return 'bg-blue-100 text-blue-800';
      case 'P5':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'triggered':
        return 'bg-red-100 text-red-800';
      case 'recovered':
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
          <Dog className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Datadog告警</h1>
            <p className="text-sm text-gray-500">管理和监控Datadog告警</p>
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
              Datadog配置状态
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
                <div className="text-sm text-gray-500 mb-1">API密钥</div>
                <div className="text-sm font-mono">{configData.apiKey ? '••••••••' : '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">应用密钥</div>
                <div className="text-sm font-mono">{configData.appKey ? '••••••••' : '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">站点</div>
                <div className="text-sm font-mono">{configData.site}</div>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
              <Select
                value={filters.priority}
                onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="P1">P1 - 严重</option>
                <option value="P2">P2 - 高</option>
                <option value="P3">P3 - 中</option>
                <option value="P4">P4 - 低</option>
                <option value="P5">P5 - 信息</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <Select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="triggered">触发中</option>
                <option value="recovered">已恢复</option>
                <option value="no_data">无数据</option>
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
                <TableHead>优先级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>创建者</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAlerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState
                      title="没有告警"
                      description="当前没有符合条件的Datadog告警"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAlerts.map((alert) => (
                  <TableRow key={alert.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{alert.name}</TableCell>
                    <TableCell>
                      <Badge className={getPriorityColor(alert.priority)}>
                        {alert.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(alert.status)}>
                        {alert.status === 'triggered' ? '触发中' : alert.status === 'recovered' ? '已恢复' : '无数据'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{alert.type}</TableCell>
                    <TableCell className="text-sm">{alert.creator}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(alert.created).toLocaleString()}
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
                  <Badge className={getPriorityColor(selectedAlert.priority)}>
                    {selectedAlert.priority}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={getStatusColor(selectedAlert.status)}>
                    {selectedAlert.status}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                <div className="text-sm">{selectedAlert.type}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">查询</label>
                <div className="text-sm bg-gray-100 p-2 rounded font-mono">{selectedAlert.query}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">消息</label>
                <div className="text-sm bg-gray-100 p-2 rounded">{selectedAlert.message}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">创建者</label>
                  <div className="text-sm">{selectedAlert.creator}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">组织ID</label>
                  <div className="text-sm font-mono">{selectedAlert.org_id}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">创建时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAlert.created).toLocaleString()}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">修改时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAlert.modified).toLocaleString()}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">多条件</label>
                  <Badge className={selectedAlert.multi ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                    {selectedAlert.multi ? '是' : '否'}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">静音</label>
                  <Badge className={selectedAlert.silenced ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}>
                    {selectedAlert.silenced ? '是' : '否'}
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">无数据通知</label>
                  <Badge className={selectedAlert.notify_no_data ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                    {selectedAlert.notify_no_data ? '是' : '否'}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">重新通知间隔</label>
                  <div className="text-sm">{selectedAlert.renotify_interval} 分钟</div>
                </div>
              </div>
              {selectedAlert.dashboard_id && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">仪表盘ID</label>
                  <div className="text-sm font-mono">{selectedAlert.dashboard_id}</div>
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
            <title>Datadog配置</title>
          </DialogHeader>
          <div className="space-y-4">
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
              <label className="block text-sm font-medium text-gray-700 mb-1">应用密钥</label>
              <Input
                type="password"
                value={config.appKey}
                onChange={(e) => setConfig({ ...config, appKey: e.target.value })}
                placeholder="输入应用密钥"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">站点</label>
              <Input
                value={config.site}
                onChange={(e) => setConfig({ ...config, site: e.target.value })}
                placeholder="datadoghq.com"
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
