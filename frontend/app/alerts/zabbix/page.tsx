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
import { Server, AlertTriangle, CheckCircle, XCircle, RefreshCw, Settings } from 'lucide-react';

interface ZabbixTrigger {
  triggerid: string;
  expression: string;
  description: string;
  url?: string;
  status: '0' | '1';
  value: '0' | '1';
  priority: number;
  lastchange: string;
  comments?: string;
  error?: string;
  templateid?: string;
  state: '0' | '1';
  type: number;
  flags: number;
}

interface ZabbixHost {
  hostid: string;
  host: string;
  name: string;
  status: string;
  available: string;
}

interface ZabbixConfig {
  url: string;
  username: string;
  password: string;
  enabled: boolean;
}

export default function ZabbixAlertsPage() {
  const [selectedTrigger, setSelectedTrigger] = useState<ZabbixTrigger | null>(null);
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

  // 获取Zabbix触发器列表
  const { data: triggersData, isLoading: triggersLoading, error: triggersError, refetch: refetchTriggers } = useQuery<ZabbixTrigger[]>({
    queryKey: ['zabbix-triggers'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/zabbix');
      return resp.data.triggers || resp.data || [];
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 获取Zabbix配置
  const { data: configData, refetch: refetchConfig } = useQuery<ZabbixConfig>({
    queryKey: ['zabbix-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/zabbix/config');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  const [config, setConfig] = useState<ZabbixConfig>({
    url: '',
    username: '',
    password: '',
    enabled: false,
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (triggersError) {
      showError('Failed to load Zabbix triggers');
    }
  }, [triggersError, showError]);

  const filteredTriggers = (triggersData || []).filter((trigger) => {
    if (filters.priority !== 'all' && trigger.priority !== parseInt(filters.priority)) return false;
    if (filters.status !== 'all' && trigger.value !== filters.status) return false;
    if (debouncedSearch && !trigger.description.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleSaveConfig = async () => {
    try {
      await api.put('/api/v1/alerts/zabbix/config', config);
      showSuccess('配置已保存');
      setShowConfig(false);
      await refetchConfig();
    } catch (error) {
      showError('保存配置失败');
    }
  };

  const handleSyncTriggers = async () => {
    try {
      await api.post('/api/v1/alerts/zabbix/sync');
      showSuccess('触发器同步成功');
      await refetchTriggers();
    } catch (error) {
      showError('同步触发器失败');
    }
  };

  const getPriorityColor = (priority: number) => {
    switch (priority) {
      case 5:
        return 'bg-red-100 text-red-800';
      case 4:
        return 'bg-orange-100 text-orange-800';
      case 3:
        return 'bg-yellow-100 text-yellow-800';
      case 2:
        return 'bg-blue-100 text-blue-800';
      case 1:
        return 'bg-gray-100 text-gray-800';
      case 0:
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityLabel = (priority: number) => {
    const labels = ['未分类', '信息', '警告', '一般严重', '严重', '灾难'];
    return labels[priority] || '未分类';
  };

  const getValueColor = (value: string) => {
    switch (value) {
      case '1':
        return 'bg-red-100 text-red-800';
      case '0':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getValueLabel = (value: string) => {
    return value === '1' ? '问题' : '正常';
  };

  if (triggersLoading) {
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
          <Server className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Zabbix告警</h1>
            <p className="text-sm text-gray-500">管理和监控Zabbix触发器</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowConfig(true)} variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            配置
          </Button>
          <Button onClick={handleSyncTriggers} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            同步触发器
          </Button>
          <Button onClick={() => refetchTriggers()}>
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
              Zabbix配置状态
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
                <div className="text-sm text-gray-500 mb-1">用户名</div>
                <div className="text-sm font-mono">{configData.username || '未配置'}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">密码</div>
                <div className="text-sm font-mono">{configData.password ? '••••••••' : '未配置'}</div>
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
                <option value="5">灾难</option>
                <option value="4">严重</option>
                <option value="3">一般严重</option>
                <option value="2">警告</option>
                <option value="1">信息</option>
                <option value="0">未分类</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <Select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="1">问题</option>
                <option value="0">正常</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <Input
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="搜索触发器描述"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 触发器列表 */}
      <Card>
        <CardHeader>
          <CardTitle>触发器列表 ({filteredTriggers.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>描述</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>表达式</TableHead>
                <TableHead>最后变化</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTriggers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState
                      title="没有触发器"
                      description="当前没有符合条件的Zabbix触发器"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredTriggers.map((trigger) => (
                  <TableRow key={trigger.triggerid} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-mono text-sm">{trigger.triggerid}</TableCell>
                    <TableCell className="font-medium">{trigger.description}</TableCell>
                    <TableCell>
                      <Badge className={getPriorityColor(trigger.priority)}>
                        {getPriorityLabel(trigger.priority)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getValueColor(trigger.value)}>
                        {getValueLabel(trigger.value)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500 truncate max-w-xs">{trigger.expression}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(trigger.lastchange * 1000).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedTrigger(trigger)}
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

      {/* 触发器详情对话框 */}
      <Dialog open={!!selectedTrigger} onOpenChange={() => setSelectedTrigger(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              触发器详情
            </DialogTitle>
          </DialogHeader>
          {selectedTrigger && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">触发器ID</label>
                <div className="text-lg font-semibold font-mono">{selectedTrigger.triggerid}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <div className="text-lg font-semibold">{selectedTrigger.description}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
                  <Badge className={getPriorityColor(selectedTrigger.priority)}>
                    {getPriorityLabel(selectedTrigger.priority)}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={getValueColor(selectedTrigger.value)}>
                    {getValueLabel(selectedTrigger.value)}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">表达式</label>
                <div className="text-sm bg-gray-100 p-2 rounded font-mono">{selectedTrigger.expression}</div>
              </div>
              {selectedTrigger.url && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
                  <a href={selectedTrigger.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    {selectedTrigger.url}
                  </a>
                </div>
              )}
              {selectedTrigger.comments && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">注释</label>
                  <div className="text-sm bg-gray-100 p-2 rounded">{selectedTrigger.comments}</div>
                </div>
              )}
              {selectedTrigger.error && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">错误</label>
                  <div className="text-sm bg-red-50 p-2 rounded text-red-600">{selectedTrigger.error}</div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">最后变化</label>
                  <div className="text-sm text-gray-600">{new Date(selectedTrigger.lastchange * 1000).toLocaleString()}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                  <div className="text-sm">{selectedTrigger.type}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态标志</label>
                  <div className="text-sm">{selectedTrigger.status === '0' ? '启用' : '禁用'}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <div className="text-sm">{selectedTrigger.state === '0' ? '正常' : '未知'}</div>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedTrigger(null)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 配置对话框 */}
      <Dialog open={showConfig} onOpenChange={setShowConfig}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Zabbix配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Zabbix URL</label>
              <Input
                value={config.url}
                onChange={(e) => setConfig({ ...config, url: e.target.value })}
                placeholder="http://zabbix:8080"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
              <Input
                value={config.username}
                onChange={(e) => setConfig({ ...config, username: e.target.value })}
                placeholder="Admin"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <Input
                type="password"
                value={config.password}
                onChange={(e) => setConfig({ ...config, password: e.target.value })}
                placeholder="输入密码"
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
