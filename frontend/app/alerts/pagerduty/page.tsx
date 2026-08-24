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
import { Phone, AlertTriangle, CheckCircle, XCircle, RefreshCw, Settings, User } from 'lucide-react';

interface PagerDutyIncident {
  id: string;
  incident_number: number;
  title: string;
  status: 'triggered' | 'acknowledged' | 'resolved';
  urgency: 'high' | 'low';
  priority: string;
  service: {
    id: string;
    summary: string;
  };
  assignment: {
    assignee: {
      id: string;
      summary: string;
    };
  };
  created_at: string;
  updated_at: string;
  acknowledged_by?: string;
  resolved_by?: string;
  first_trigger_log_entry: {
    id: string;
    summary: string;
  };
}

interface PagerDutyConfig {
  apiToken: string;
  userEmail: string;
  enabled: boolean;
}

export default function PagerDutyAlertsPage() {
  const [selectedIncident, setSelectedIncident] = useState<PagerDutyIncident | null>(null);
  const [filters, setFilters] = useState({
    urgency: 'all',
    status: 'all',
    search: '',
  });
  const [showConfig, setShowConfig] = useState(false);

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 获取PagerDuty事件列表
  const { data: incidentsData, isLoading: incidentsLoading, error: incidentsError, refetch: refetchIncidents } = useQuery<PagerDutyIncident[]>({
    queryKey: ['pagerduty-incidents'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/pagerduty');
      return resp.data.incidents || resp.data || [];
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 获取PagerDuty配置
  const { data: configData, refetch: refetchConfig } = useQuery<PagerDutyConfig>({
    queryKey: ['pagerduty-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/pagerduty/config');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  const [config, setConfig] = useState<PagerDutyConfig>({
    apiToken: '',
    userEmail: '',
    enabled: false,
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (incidentsError) {
      showError('Failed to load PagerDuty incidents');
    }
  }, [incidentsError, showError]);

  const filteredIncidents = (incidentsData || []).filter((incident) => {
    if (filters.urgency !== 'all' && incident.urgency !== filters.urgency) return false;
    if (filters.status !== 'all' && incident.status !== filters.status) return false;
    if (debouncedSearch && !incident.title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleSaveConfig = async () => {
    try {
      await api.put('/api/v1/alerts/pagerduty/config', config);
      showSuccess('配置已保存');
      setShowConfig(false);
      await refetchConfig();
    } catch (error) {
      showError('保存配置失败');
    }
  };

  const handleSyncIncidents = async () => {
    try {
      await api.post('/api/v1/alerts/pagerduty/sync');
      showSuccess('事件同步成功');
      await refetchIncidents();
    } catch (error) {
      showError('同步事件失败');
    }
  };

  const handleAcknowledge = async (incidentId: string) => {
    try {
      await api.post(`/api/v1/alerts/pagerduty/${incidentId}/acknowledge`);
      showSuccess('事件已确认');
      await refetchIncidents();
    } catch (error) {
      showError('确认事件失败');
    }
  };

  const handleResolve = async (incidentId: string) => {
    try {
      await api.post(`/api/v1/alerts/pagerduty/${incidentId}/resolve`);
      showSuccess('事件已解决');
      await refetchIncidents();
    } catch (error) {
      showError('解决事件失败');
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'triggered':
        return 'bg-red-100 text-red-800';
      case 'acknowledged':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (incidentsLoading) {
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
          <Phone className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">PagerDuty告警</h1>
            <p className="text-sm text-gray-500">管理和监控PagerDuty事件</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowConfig(true)} variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            配置
          </Button>
          <Button onClick={handleSyncIncidents} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            同步事件
          </Button>
          <Button onClick={() => refetchIncidents()}>
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
              PagerDuty配置状态
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
                <div className="text-sm text-gray-500 mb-1">API令牌</div>
                <div className="text-sm font-mono">{configData.apiToken ? '••••••••' : '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">用户邮箱</div>
                <div className="text-sm font-mono">{configData.userEmail || '未配置'}</div>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">紧急程度</label>
              <Select
                value={filters.urgency}
                onChange={(e) => setFilters({ ...filters, urgency: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="high">高</option>
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
                <option value="triggered">触发中</option>
                <option value="acknowledged">已确认</option>
                <option value="resolved">已解决</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <Input
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="搜索事件标题"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 事件列表 */}
      <Card>
        <CardHeader>
          <CardTitle>事件列表 ({filteredIncidents.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>编号</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>紧急程度</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>负责人</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredIncidents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState
                      title="没有事件"
                      description="当前没有符合条件的PagerDuty事件"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredIncidents.map((incident) => (
                  <TableRow key={incident.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-mono text-sm">#{incident.incident_number}</TableCell>
                    <TableCell className="font-medium">{incident.title}</TableCell>
                    <TableCell>
                      <Badge className={getUrgencyColor(incident.urgency)}>
                        {incident.urgency === 'high' ? '高' : '低'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(incident.status)}>
                        {incident.status === 'triggered' ? '触发中' : incident.status === 'acknowledged' ? '已确认' : '已解决'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{incident.service?.summary || '-'}</TableCell>
                    <TableCell className="text-sm">
                      {incident.assignment?.assignee?.summary || '-'}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(incident.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedIncident(incident)}
                        >
                          详情
                        </Button>
                        {incident.status === 'triggered' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleAcknowledge(incident.id)}
                          >
                            确认
                          </Button>
                        )}
                        {incident.status !== 'resolved' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleResolve(incident.id)}
                          >
                            解决
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

      {/* 事件详情对话框 */}
      <Dialog open={!!selectedIncident} onOpenChange={() => setSelectedIncident(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              事件详情
            </DialogTitle>
          </DialogHeader>
          {selectedIncident && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">事件编号</label>
                <div className="text-lg font-semibold">#{selectedIncident.incident_number}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                <div className="text-lg font-semibold">{selectedIncident.title}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">紧急程度</label>
                  <Badge className={getUrgencyColor(selectedIncident.urgency)}>
                    {selectedIncident.urgency === 'high' ? '高' : '低'}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={getStatusColor(selectedIncident.status)}>
                    {selectedIncident.status}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
                <div className="text-sm">{selectedIncident.priority || '-'}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
                <div className="text-sm">{selectedIncident.service?.summary || '-'}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">负责人</label>
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  <span className="text-sm">{selectedIncident.assignment?.assignee?.summary || '-'}</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">创建时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedIncident.created_at).toLocaleString()}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">更新时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedIncident.updated_at).toLocaleString()}</div>
                </div>
              </div>
              {selectedIncident.acknowledged_by && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">确认人</label>
                  <div className="text-sm">{selectedIncident.acknowledged_by}</div>
                </div>
              )}
              {selectedIncident.resolved_by && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">解决人</label>
                  <div className="text-sm">{selectedIncident.resolved_by}</div>
                </div>
              )}
              {selectedIncident.first_trigger_log_entry && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">首次触发日志</label>
                  <div className="text-sm bg-gray-100 p-2 rounded">{selectedIncident.first_trigger_log_entry.summary}</div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedIncident(null)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 配置对话框 */}
      <Dialog open={showConfig} onOpenChange={setShowConfig}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>PagerDuty配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API令牌</label>
              <Input
                type="password"
                value={config.apiToken}
                onChange={(e) => setConfig({ ...config, apiToken: e.target.value })}
                placeholder="输入API令牌"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">用户邮箱</label>
              <Input
                value={config.userEmail}
                onChange={(e) => setConfig({ ...config, userEmail: e.target.value })}
                placeholder="user@example.com"
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
