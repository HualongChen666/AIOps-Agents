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
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Shield, AlertTriangle, Terminal, Activity, Lock, Eye, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface SecurityEvent {
  id: string;
  timestamp: string;
  type: 'compliance' | 'threat' | 'vulnerability' | 'incident';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  source: string;
  affectedAssets: number;
  status: 'open' | 'resolved';
}

interface SecurityStats {
  total: number;
  threat_count: number;
  vulnerability_count: number;
  compliance_rate: number;
  affected_assets: number;
  blocked_count: number;
  high_count: number;
  block_rate: number;
  level_counts: Record<string, number>;
}

interface CommandCheckResult {
  command: string;
  risk_level: 'safe' | 'low' | 'medium' | 'high' | 'blocked';
  risk_name: string;
  reason: string;
  action: string;
  safe_alternative: string;
  is_chained: boolean;
  chain_count: number;
  audit: {
    executor: string;
    source_ip: string;
    recorded: boolean;
  };
}

interface CommandRewriteResult {
  original: string;
  rewritten: string;
  changed: boolean;
  message: string;
}

export default function SecurityCenterPage() {
  const [activeTab, setActiveTab] = useState<'events' | 'stats' | 'check' | 'rewrite'>('events');
  const [command, setCommand] = useState('');
  const [targetHost, setTargetHost] = useState('');
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<CommandCheckResult | null>(null);
  const [rewriteResult, setRewriteResult] = useState<CommandRewriteResult | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);

  // 🔧 获取安全事件列表
  const { data: eventsData, isLoading: eventsLoading, error: eventsError, refetch: refetchEvents } = useQuery<{
    events: SecurityEvent[];
  }>({
    queryKey: ['security-events'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/events?limit=100');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 获取安全统计
  const { data: statsData, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useQuery<SecurityStats>({
    queryKey: ['security-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/stats?limit=5000');
      return resp.data;
    },
    refetchInterval: 120000, // 120秒刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(eventsLoading || statsLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 规范化事件数据
  const [events, setEvents] = useState<SecurityEvent[]>([]);

  useEffect(() => {
    if (eventsData?.events) {
      setEvents(eventsData.events);
    }
  }, [eventsData]);

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (eventsError) {
      showError('Failed to load security events');
      setPageError(eventsError as Error);
    }
    if (statsError) {
      showError('Failed to load security stats');
      setPageError(statsError as Error);
    }
  }, [eventsError, statsError, showError, setPageError]);

  const handleCheckCommand = async () => {
    if (!command.trim()) {
      showError('请输入命令');
      return;
    }

    setChecking(true);
    try {
      const payload: any = { command };
      if (targetHost) {
        payload.target_host = targetHost;
      }

      const response = await api.post('/api/guard/check', payload);
      setCheckResult(response.data);
      showSuccess('命令检查完成');
    } catch (error) {
      showError('命令检查失败');
    } finally {
      setChecking(false);
    }
  };

  const handleRewriteCommand = async () => {
    if (!command.trim()) {
      showError('请输入命令');
      return;
    }

    setChecking(true);
    try {
      const response = await api.post('/api/guard/rewrite', { command });
      setRewriteResult(response.data);
      showSuccess('命令改写完成');
    } catch (error) {
      showError('命令改写失败');
    } finally {
      setChecking(false);
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

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'compliance':
        return 'bg-purple-100 text-purple-800';
      case 'threat':
        return 'bg-red-100 text-red-800';
      case 'vulnerability':
        return 'bg-orange-100 text-orange-800';
      case 'incident':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'safe':
        return 'bg-green-100 text-green-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'blocked':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'events' as const, label: '安全事件', icon: AlertTriangle },
    { key: 'stats' as const, label: '安全统计', icon: Activity },
    { key: 'check' as const, label: '命令检查', icon: Terminal },
    { key: 'rewrite' as const, label: '命令改写', icon: Lock },
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
          description="无法加载安全数据，请稍后重试"
          action={<Button onClick={() => { refetchEvents(); refetchStats(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchEvents(); refetchStats(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">安全中心</h1>
            <p className="text-sm text-gray-500">监控和管理系统安全事件</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchEvents(); refetchStats(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
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

      {activeTab === 'events' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              安全事件列表 ({events.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {eventsLoading ? (
              <LoadingSpinner />
            ) : events.length === 0 ? (
              <EmptyState
                title="暂无安全事件"
                description="当前没有安全事件记录"
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>严重度</TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((event) => (
                    <TableRow key={event.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="text-sm text-gray-500">
                        {new Date(event.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge className={getTypeColor(event.type)}>
                          {event.type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getSeverityColor(event.severity)}>
                          {event.severity}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{event.title}</TableCell>
                      <TableCell>{event.source}</TableCell>
                      <TableCell>
                        <Badge variant={event.status === 'open' ? 'destructive' : 'default'}>
                          {event.status === 'open' ? '未处理' : '已解决'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedEvent(event)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          查看
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'stats' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              安全统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsData ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">总事件数</div>
                  <div className="text-2xl font-bold text-[var(--accent-blue)]">{statsData.total}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">威胁事件</div>
                  <div className="text-2xl font-bold text-[var(--accent-red)]">{statsData.threat_count}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">漏洞事件</div>
                  <div className="text-2xl font-bold text-[var(--accent-yellow)]">{statsData.vulnerability_count}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">合规率</div>
                  <div className="text-2xl font-bold text-[var(--accent-green)]">{statsData.compliance_rate}%</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">受影响资产</div>
                  <div className="text-2xl font-bold text-[var(--accent-purple)]">{statsData.affected_assets}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">拦截次数</div>
                  <div className="text-2xl font-bold text-[var(--accent-red)]">{statsData.blocked_count}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">高危事件</div>
                  <div className="text-2xl font-bold text-[var(--accent-orange)]">{statsData.high_count}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">拦截率</div>
                  <div className="text-2xl font-bold text-[var(--accent-cyan)]">{statsData.block_rate}%</div>
                </div>
              </div>
            ) : (
              <EmptyState
                title="暂无统计数据"
                description="当前没有可用的安全统计数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'check' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              命令风险检查
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">命令</label>
                <Input
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="输入要检查的命令，例如: rm -rf /tmp/cache"
                  className="font-mono"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">目标主机（可选）</label>
                <Input
                  value={targetHost}
                  onChange={(e) => setTargetHost(e.target.value)}
                  placeholder="输入目标主机名"
                />
              </div>
              <Button onClick={handleCheckCommand} disabled={checking || !command.trim()}>
                {checking ? '检查中...' : '检查命令'}
              </Button>

              {checkResult && (
                <div className="mt-6 p-4 border rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">检查结果</h3>
                    <Badge className={getRiskLevelColor(checkResult.risk_level)}>
                      {checkResult.risk_level}
                    </Badge>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">风险名称</label>
                    <p className="mt-1 text-sm text-gray-900">{checkResult.risk_name}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">原因</label>
                    <p className="mt-1 text-sm text-gray-900">{checkResult.reason}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">建议操作</label>
                    <p className="mt-1 text-sm text-gray-900">{checkResult.action}</p>
                  </div>
                  {checkResult.safe_alternative && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">安全替代方案</label>
                      <p className="mt-1 text-sm text-gray-900 font-mono bg-gray-100 p-2 rounded">
                        {checkResult.safe_alternative}
                      </p>
                    </div>
                  )}
                  <div className="flex gap-4 text-sm text-gray-500">
                    <span>链式命令: {checkResult.is_chained ? '是' : '否'}</span>
                    <span>链长度: {checkResult.chain_count}</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'rewrite' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              命令安全改写
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">命令</label>
                <Input
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="输入要改写的命令，例如: rm -rf /tmp/old_data"
                  className="font-mono"
                />
              </div>
              <Button onClick={handleRewriteCommand} disabled={checking || !command.trim()}>
                {checking ? '改写中...' : '改写命令'}
              </Button>

              {rewriteResult && (
                <div className="mt-6 p-4 border rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">改写结果</h3>
                    {rewriteResult.changed ? (
                      <Badge variant="default">已改写</Badge>
                    ) : (
                      <Badge variant="secondary">无需改写</Badge>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">原始命令</label>
                    <p className="mt-1 text-sm text-gray-900 font-mono bg-gray-100 p-2 rounded">
                      {rewriteResult.original}
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">改写后命令</label>
                    <p className="mt-1 text-sm text-gray-900 font-mono bg-green-50 p-2 rounded">
                      {rewriteResult.rewritten}
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">说明</label>
                    <p className="mt-1 text-sm text-gray-900">{rewriteResult.message}</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 安全事件详情弹窗 */}
      {selectedEvent && (
        <Dialog open={!!selectedEvent} onOpenChange={() => setSelectedEvent(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>安全事件详情 - {selectedEvent.id}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">时间</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {new Date(selectedEvent.timestamp).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">类型</label>
                  <Badge className={getTypeColor(selectedEvent.type)}>
                    {selectedEvent.type}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">严重度</label>
                  <Badge className={getSeverityColor(selectedEvent.severity)}>
                    {selectedEvent.severity}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">状态</label>
                  <Badge variant={selectedEvent.status === 'open' ? 'destructive' : 'default'}>
                    {selectedEvent.status === 'open' ? '未处理' : '已解决'}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">标题</label>
                <p className="mt-1 text-sm text-gray-900">{selectedEvent.title}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">描述</label>
                <p className="mt-1 text-sm text-gray-900">{selectedEvent.description}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">来源</label>
                <p className="mt-1 text-sm text-gray-900">{selectedEvent.source}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">受影响资产</label>
                <p className="mt-1 text-sm text-gray-900">{selectedEvent.affectedAssets}</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedEvent(null)}>
                关闭
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}