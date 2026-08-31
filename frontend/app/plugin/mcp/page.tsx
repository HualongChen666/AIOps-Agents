'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { 
  Server, 
  Activity, 
  Search, 
  TrendingUp, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Zap,
  Shield,
  Database
} from 'lucide-react';

interface HostHealth {
  host_id: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  last_updated: string;
}

interface IncidentRecord {
  id: string;
  alert_id: string;
  title: string;
  severity: string;
  status: string;
  timestamp: string;
  resolution?: string;
}

interface MetricsData {
  host_id: string;
  metrics: Record<string, number>;
  timestamp: string;
}

interface RepairRequest {
  alert_id: string;
  user: string;
  comment?: string;
}

interface RepairResponse {
  alert_id: string;
  status: string;
  success: boolean;
  fix_applied: boolean;
  verification?: any;
  error?: string;
}

export default function MCPPage() {
  const [selectedHost, setSelectedHost] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedIncident, setSelectedIncident] = useState<IncidentRecord | null>(null);
  const [repairDialogOpen, setRepairDialogOpen] = useState(false);
  const [repairComment, setRepairComment] = useState<string>('');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['cpu_usage', 'memory_usage']);
  
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  
  const debouncedSearch = useDebounce(searchQuery, 300);

  // 获取主机健康状态
  const { data: hostHealth, isLoading: healthLoading, refetch: refetchHealth } = useQuery<HostHealth>({
    queryKey: ['mcp-host-health', selectedHost],
    queryFn: async () => {
      if (!selectedHost) return null;
      const resp = await api.post('/api/mcp/get_host_health', { host_id: selectedHost });
      return resp.data;
    },
    enabled: !!selectedHost,
    refetchInterval: 30000,
  });

  // 搜索历史事件
  const { data: incidentHistory, isLoading: historyLoading, refetch: refetchHistory } = useQuery<{ incidents: IncidentRecord[] }>({
    queryKey: ['mcp-incident-history', debouncedSearch],
    queryFn: async () => {
      const resp = await api.post('/api/mcp/search_incident_history', { 
        query: debouncedSearch || '',
        limit: 20 
      });
      return resp.data;
    },
    enabled: true,
    refetchInterval: 60000,
  });

  // 获取指标数据
  const { data: metricsData, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery<MetricsData>({
    queryKey: ['mcp-metrics', selectedHost, selectedMetrics],
    queryFn: async () => {
      if (!selectedHost || selectedMetrics.length === 0) return null;
      const resp = await api.post('/api/mcp/get_metrics', { 
        host_id: selectedHost,
        metrics: selectedMetrics 
      });
      return resp.data;
    },
    enabled: !!selectedHost && selectedMetrics.length > 0,
    refetchInterval: 15000,
  });

  const { isLoading: pageLoading, error: pageError } = useLoadingState(healthLoading || historyLoading || metricsLoading);

  const handleTriggerRepair = async () => {
    if (!selectedIncident) return;
    
    try {
      const repairRequest: RepairRequest = {
        alert_id: selectedIncident.alert_id,
        user: 'admin', // TODO: 从用户上下文获取
        comment: repairComment || undefined,
      };
      
      const resp = await api.post('/api/mcp/trigger_repair_with_hitl', repairRequest);
      const result = resp.data as RepairResponse;
      
      if (result.success) {
        showSuccess(`修复任务已启动: ${result.status}`);
        setRepairDialogOpen(false);
        setRepairComment('');
        refetchHistory();
      } else {
        showError(`修复失败: ${result.error || '未知错误'}`);
      }
    } catch (error: any) {
      showError(`触发修复失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleApproveRepair = async (repairId: string, approved: boolean) => {
    try {
      const resp = await api.post('/api/mcp/approve_repair', {
        repair_id: repairId,
        approved,
        comment: approved ? '批准修复' : '拒绝修复',
      });
      
      if (resp.data.success) {
        showSuccess(approved ? '修复已批准' : '修复已拒绝');
        refetchHistory();
      }
    } catch (error: any) {
      showError(`操作失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'unhealthy':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'fatal':
        return 'bg-red-100 text-red-800';
      case 'high':
      case 'warning':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
      case 'info':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
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
          description="无法加载MCP数据，请稍后重试"
          action={<Button onClick={() => { refetchHealth(); refetchHistory(); refetchMetrics(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchHealth(); refetchHistory(); refetchMetrics(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Server className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">MCP协议管理</h1>
            <p className="text-sm text-gray-500">Multi-Channel Protocol 多通道协议管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchHealth(); refetchHistory(); refetchMetrics(); }} variant="outline">
            刷新
          </Button>
        </div>
      </div>

      {/* 主机选择和健康状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            主机健康监控
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">主机ID</label>
                <Input
                  value={selectedHost}
                  onChange={(e) => setSelectedHost(e.target.value)}
                  placeholder="输入主机ID (例如: host-001)"
                />
              </div>
              <div className="flex items-end">
                <Button onClick={() => refetchHealth()}>
                  查询健康状态
                </Button>
              </div>
            </div>

            {hostHealth && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">状态</div>
                  <Badge className={getHealthStatusColor(hostHealth.status)}>
                    {hostHealth.status}
                  </Badge>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">CPU使用率</div>
                  <div className="text-2xl font-bold text-[var(--accent-blue)]">
                    {hostHealth.cpu_usage?.toFixed(1) || 0}%
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">内存使用率</div>
                  <div className="text-2xl font-bold text-[var(--accent-green)]">
                    {hostHealth.memory_usage?.toFixed(1) || 0}%
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">磁盘使用率</div>
                  <div className="text-2xl font-bold text-[var(--accent-yellow)]">
                    {hostHealth.disk_usage?.toFixed(1) || 0}%
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 指标监控 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            实时指标监控
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">选择指标</label>
                <Select
                  multiple
                  value={selectedMetrics}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions).map(opt => opt.value);
                    setSelectedMetrics(values);
                  }}
                  className="w-full"
                >
                  <option value="cpu_usage">CPU使用率</option>
                  <option value="memory_usage">内存使用率</option>
                  <option value="disk_usage">磁盘使用率</option>
                  <option value="network_in">网络入流量</option>
                  <option value="network_out">网络出流量</option>
                  <option value="request_rate">请求速率</option>
                  <option value="error_rate">错误率</option>
                </Select>
              </div>
              <div className="flex items-end">
                <Button onClick={() => refetchMetrics()}>
                  获取指标
                </Button>
              </div>
            </div>

            {metricsData && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                {Object.entries(metricsData.metrics).map(([key, value]) => (
                  <div key={key} className="p-4 border rounded-lg">
                    <div className="text-sm text-gray-500 mb-1">{key}</div>
                    <div className="text-2xl font-bold text-[var(--accent-blue)]">
                      {typeof value === 'number' ? value.toFixed(2) : value}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 历史事件搜索 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            历史事件搜索
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">搜索关键词</label>
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="输入关键词搜索历史事件"
                />
              </div>
              <div className="flex items-end">
                <Button onClick={() => refetchHistory()}>
                  搜索
                </Button>
              </div>
            </div>

            {incidentHistory && incidentHistory.incidents && incidentHistory.incidents.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>告警ID</TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead>严重度</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {incidentHistory.incidents.map((incident) => (
                    <TableRow key={incident.id}>
                      <TableCell className="font-mono text-sm">{incident.id}</TableCell>
                      <TableCell className="font-mono text-sm">{incident.alert_id}</TableCell>
                      <TableCell className="font-medium">{incident.title}</TableCell>
                      <TableCell>
                        <Badge className={getSeverityColor(incident.severity)}>
                          {incident.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={incident.status === 'resolved' ? 'default' : 'secondary'}>
                          {incident.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(incident.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedIncident(incident);
                            setRepairDialogOpen(true);
                          }}
                        >
                          <Zap className="h-4 w-4 mr-1" />
                          触发修复
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState
                title="没有找到历史事件"
                description="尝试使用不同的关键词搜索"
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* 修复对话框 */}
      <Dialog open={repairDialogOpen} onOpenChange={setRepairDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              触发自动修复
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedIncident && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm font-medium mb-2">事件信息</div>
                <div className="space-y-1 text-sm">
                  <div><span className="text-gray-500">告警ID:</span> {selectedIncident.alert_id}</div>
                  <div><span className="text-gray-500">标题:</span> {selectedIncident.title}</div>
                  <div><span className="text-gray-500">严重度:</span> {selectedIncident.severity}</div>
                </div>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">修复备注</label>
              <Input
                value={repairComment}
                onChange={(e) => setRepairComment(e.target.value)}
                placeholder="输入修复备注（可选）"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRepairDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleTriggerRepair}>
              <Zap className="h-4 w-4 mr-2" />
              触发修复
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 功能说明 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            MCP协议功能说明
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-[var(--accent-blue)]" />
                <div className="font-medium">主机健康监控</div>
              </div>
              <div className="text-sm text-gray-600">
                实时获取主机的CPU、内存、磁盘使用率等健康指标
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-[var(--accent-green)]" />
                <div className="font-medium">实时指标监控</div>
              </div>
              <div className="text-sm text-gray-600">
                支持自定义指标集合，批量获取多个指标的实时数据
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Search className="h-4 w-4 text-[var(--accent-yellow)]" />
                <div className="font-medium">历史事件搜索</div>
              </div>
              <div className="text-sm text-gray-600">
                基于关键词搜索历史告警和修复记录
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-4 w-4 text-[var(--accent-cyan)]" />
                <div className="font-medium">自动修复触发</div>
              </div>
              <div className="text-sm text-gray-600">
                支持带人工审核流程的自动修复任务触发
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
