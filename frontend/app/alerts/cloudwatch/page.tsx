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
import { Cloud, AlertTriangle, CheckCircle, XCircle, RefreshCw, Settings } from 'lucide-react';

interface CloudWatchAlarm {
  alarmName: string;
  alarmArn: string;
  alarmDescription?: string;
  awsAccountId: string;
  alarmConfigurationUpdatedTimestamp: string;
  stateValue: 'OK' | 'ALARM' | 'INSUFFICIENT_DATA';
  stateReason: string;
  stateReasonData?: string;
  stateUpdatedTimestamp: string;
  metricName: string;
  namespace: string;
  statistic: string;
  period: number;
  evaluationPeriods: number;
  threshold: number;
  comparisonOperator: string;
  treatMissingData: string;
  actionsEnabled: boolean;
  okActions?: string[];
  alarmActions?: string[];
  insufficientDataActions?: string[];
  dimensions: Array<{ name: string; value: string }>;
}

interface CloudWatchConfig {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
  enabled: boolean;
}

export default function CloudWatchAlertsPage() {
  const [selectedAlarm, setSelectedAlarm] = useState<CloudWatchAlarm | null>(null);
  const [filters, setFilters] = useState({
    state: 'all',
    namespace: '',
    search: '',
  });
  const [showConfig, setShowConfig] = useState(false);

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 获取CloudWatch告警列表
  const { data: alarmsData, isLoading: alarmsLoading, error: alarmsError, refetch: refetchAlarms } = useQuery<CloudWatchAlarm[]>({
    queryKey: ['cloudwatch-alarms'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/cloudwatch');
      return resp.data.alarms || resp.data || [];
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 获取CloudWatch配置
  const { data: configData, refetch: refetchConfig } = useQuery<CloudWatchConfig>({
    queryKey: ['cloudwatch-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/cloudwatch/config');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  const [config, setConfig] = useState<CloudWatchConfig>({
    accessKeyId: '',
    secretAccessKey: '',
    region: 'us-east-1',
    enabled: false,
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (alarmsError) {
      showError('Failed to load CloudWatch alarms');
    }
  }, [alarmsError, showError]);

  const filteredAlarms = (alarmsData || []).filter((alarm) => {
    if (filters.state !== 'all' && alarm.stateValue !== filters.state) return false;
    if (filters.namespace && !alarm.namespace.includes(filters.namespace)) return false;
    if (debouncedSearch && !alarm.alarmName.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleSaveConfig = async () => {
    try {
      await api.put('/api/v1/alerts/cloudwatch/config', config);
      showSuccess('配置已保存');
      setShowConfig(false);
      await refetchConfig();
    } catch (error) {
      showError('保存配置失败');
    }
  };

  const handleSyncAlarms = async () => {
    try {
      await api.post('/api/v1/alerts/cloudwatch/sync');
      showSuccess('告警同步成功');
      await refetchAlarms();
    } catch (error) {
      showError('同步告警失败');
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'ALARM':
        return 'bg-red-100 text-red-800';
      case 'OK':
        return 'bg-green-100 text-green-800';
      case 'INSUFFICIENT_DATA':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (alarmsLoading) {
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
          <Cloud className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">CloudWatch告警</h1>
            <p className="text-sm text-gray-500">管理和监控AWS CloudWatch告警</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowConfig(true)} variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            配置
          </Button>
          <Button onClick={handleSyncAlarms} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            同步告警
          </Button>
          <Button onClick={() => refetchAlarms()}>
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
              CloudWatch配置状态
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
                <div className="text-sm text-gray-500 mb-1">访问密钥ID</div>
                <div className="text-sm font-mono">{configData.accessKeyId ? '••••••••' : '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">密钥</div>
                <div className="text-sm font-mono">{configData.secretAccessKey ? '••••••••' : '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">区域</div>
                <div className="text-sm font-mono">{configData.region}</div>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <Select
                value={filters.state}
                onChange={(e) => setFilters({ ...filters, state: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="ALARM">告警</option>
                <option value="OK">正常</option>
                <option value="INSUFFICIENT_DATA">数据不足</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">命名空间</label>
              <Input
                value={filters.namespace}
                onChange={(e) => setFilters({ ...filters, namespace: e.target.value })}
                placeholder="输入命名空间"
              />
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
          <CardTitle>告警列表 ({filteredAlarms.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>命名空间</TableHead>
                <TableHead>指标</TableHead>
                <TableHead>阈值</TableHead>
                <TableHead>账户ID</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAlarms.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState
                      title="没有告警"
                      description="当前没有符合条件的CloudWatch告警"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAlarms.map((alarm) => (
                  <TableRow key={alarm.alarmArn} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{alarm.alarmName}</TableCell>
                    <TableCell>
                      <Badge className={getStateColor(alarm.stateValue)}>
                        {alarm.stateValue === 'ALARM' ? '告警' : alarm.stateValue === 'OK' ? '正常' : '数据不足'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{alarm.namespace}</TableCell>
                    <TableCell className="text-sm">{alarm.metricName}</TableCell>
                    <TableCell className="font-mono text-sm">{alarm.threshold}</TableCell>
                    <TableCell className="font-mono text-sm">{alarm.awsAccountId}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(alarm.stateUpdatedTimestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedAlarm(alarm)}
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
      <Dialog open={!!selectedAlarm} onOpenChange={() => setSelectedAlarm(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              告警详情
            </DialogTitle>
          </DialogHeader>
          {selectedAlarm && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警名称</label>
                <div className="text-lg font-semibold">{selectedAlarm.alarmName}</div>
              </div>
              {selectedAlarm.alarmDescription && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                  <div className="text-sm">{selectedAlarm.alarmDescription}</div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={getStateColor(selectedAlarm.stateValue)}>
                    {selectedAlarm.stateValue}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">账户ID</label>
                  <div className="text-sm font-mono">{selectedAlarm.awsAccountId}</div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">状态原因</label>
                <div className="text-sm bg-gray-100 p-2 rounded">{selectedAlarm.stateReason}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">命名空间</label>
                  <div className="text-sm">{selectedAlarm.namespace}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">指标</label>
                  <div className="text-sm">{selectedAlarm.metricName}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">统计</label>
                  <div className="text-sm">{selectedAlarm.statistic}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">周期</label>
                  <div className="text-sm">{selectedAlarm.period} 秒</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">评估周期</label>
                  <div className="text-sm">{selectedAlarm.evaluationPeriods}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">阈值</label>
                  <div className="text-sm font-mono">{selectedAlarm.threshold}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">比较操作符</label>
                  <div className="text-sm">{selectedAlarm.comparisonOperator}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">缺失数据处理</label>
                  <div className="text-sm">{selectedAlarm.treatMissingData}</div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">操作启用</label>
                <Badge className={selectedAlarm.actionsEnabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                  {selectedAlarm.actionsEnabled ? '是' : '否'}
                </Badge>
              </div>
              {selectedAlarm.dimensions && selectedAlarm.dimensions.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">维度</label>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>名称</TableHead>
                        <TableHead>值</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedAlarm.dimensions.map((dim, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-sm">{dim.name}</TableCell>
                          <TableCell className="font-mono text-sm">{dim.value}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">配置更新时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAlarm.alarmConfigurationUpdatedTimestamp).toLocaleString()}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态更新时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAlarm.stateUpdatedTimestamp).toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedAlarm(null)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 配置对话框 */}
      <Dialog open={showConfig} onOpenChange={setShowConfig}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>CloudWatch配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">访问密钥ID</label>
              <Input
                value={config.accessKeyId}
                onChange={(e) => setConfig({ ...config, accessKeyId: e.target.value })}
                placeholder="输入访问密钥ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">密钥</label>
              <Input
                type="password"
                value={config.secretAccessKey}
                onChange={(e) => setConfig({ ...config, secretAccessKey: e.target.value })}
                placeholder="输入密钥"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">区域</label>
              <Input
                value={config.region}
                onChange={(e) => setConfig({ ...config, region: e.target.value })}
                placeholder="us-east-1"
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
