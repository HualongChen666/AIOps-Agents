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
import { Wrench, History, Play, Settings, RefreshCw, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

interface RepairScript {
  key: string;
  name: string;
  description?: string;
  platform: string;
}

interface RepairRecord {
  id: string;
  platform: string;
  script_key: string;
  script_name: string;
  host_name?: string;
  success: boolean;
  output?: string;
  error?: string;
  exit_code?: number;
  duration_sec?: number;
  timestamp: string;
  blocked?: boolean;
  safe_alternative?: string;
}

export default function RepairsPage() {
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [selectedScript, setSelectedScript] = useState<string>('');
  const [hostName, setHostName] = useState<string>('');
  const [params, setParams] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [showExecuteDialog, setShowExecuteDialog] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<RepairRecord | null>(null);

  // 🔧 获取修复脚本列表
  const { data: scriptsData, isLoading: scriptsLoading, error: scriptsError, refetch: refetchScripts } = useQuery<{
    scripts: Record<string, RepairScript[]> | RepairScript[];
  }>({
    queryKey: ['repair-scripts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repairs/scripts');
      return resp.data;
    },
    refetchInterval: 120000, // 120秒刷新
  });

  // 🔧 获取修复历史记录
  const { data: historyData, isLoading: historyLoading, error: historyError, refetch: refetchHistory } = useQuery<{
    total: number;
    records: RepairRecord[];
  }>({
    queryKey: ['repair-history'],
    queryFn: async () => {
      const platform = selectedPlatform === 'all' ? undefined : selectedPlatform;
      const resp = await api.get(`/api/v1/repairs/history?limit=100${platform ? `&platform=${platform}` : ''}`);
      return resp.data;
    },
    refetchInterval: 30000, // 30秒刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(scriptsLoading || historyLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 规范化脚本数据
  const [scripts, setScripts] = useState<RepairScript[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);

  useEffect(() => {
    if (scriptsData?.scripts) {
      const scriptsMap = scriptsData.scripts;
      let allScripts: RepairScript[] = [];
      let uniquePlatforms: string[] = [];

      if (typeof scriptsMap === 'object' && !Array.isArray(scriptsMap)) {
        // { windows: [...], linux: [...] }
        Object.entries(scriptsMap).forEach(([platform, platformScripts]) => {
          uniquePlatforms.push(platform);
          if (Array.isArray(platformScripts)) {
            allScripts = allScripts.concat(
              platformScripts.map((s: any) => ({
                key: s.key,
                name: s.name,
                description: s.description,
                platform,
              }))
            );
          }
        });
      } else if (Array.isArray(scriptsMap)) {
        // [...]
        allScripts = scriptsMap.map((s: any) => ({
          key: s.key,
          name: s.name,
          description: s.description,
          platform: s.platform || 'unknown',
        }));
        uniquePlatforms = [...new Set(allScripts.map(s => s.platform))];
      }

      setScripts(allScripts);
      setPlatforms(uniquePlatforms);
    }
  }, [scriptsData]);

  // 🔧 规范化历史记录数据
  const [history, setHistory] = useState<RepairRecord[]>([]);

  useEffect(() => {
    if (historyData?.records) {
      const records = historyData.records.map((r: any) => ({
        id: r.id || `${r.timestamp}-${r.script_key}`,
        platform: r.platform || 'unknown',
        script_key: r.script_key || r.script || 'unknown',
        script_name: r.script_name || r.script || 'unknown',
        host_name: r.host_name,
        success: r.success !== false,
        output: r.output,
        error: r.error,
        exit_code: r.exit_code,
        duration_sec: r.duration_sec,
        timestamp: r.timestamp || r.created_at || new Date().toISOString(),
        blocked: r.blocked,
        safe_alternative: r.safe_alternative,
      }));
      setHistory(records);
    }
  }, [historyData]);

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (scriptsError) {
      showError('Failed to load repair scripts');
      setPageError(scriptsError as Error);
    }
    if (historyError) {
      showError('Failed to load repair history');
      setPageError(historyError as Error);
    }
  }, [scriptsError, historyError, showError, setPageError]);

  const filteredScripts = selectedPlatform === 'all'
    ? scripts
    : scripts.filter(s => s.platform === selectedPlatform);

  const handleExecute = async () => {
    if (!selectedScript) {
      showError('请选择修复脚本');
      return;
    }

    setExecuting(true);
    try {
      const platform = selectedPlatform === 'all' ? 'linux' : selectedPlatform;
      const payload: any = {
        platform,
        script_key: selectedScript,
        params,
      };
      if (hostName) {
        payload.host_name = hostName;
      }

      const response = await api.post('/api/v1/repairs/execute', payload);
      showSuccess('修复脚本执行成功');
      setShowExecuteDialog(false);
      setSelectedScript('');
      setHostName('');
      setParams({});
      await refetchHistory();
    } catch (error: any) {
      if (error.response?.status === 403) {
        showError(`修复被护栏拦截: ${error.response?.data?.detail || '未知原因'}`);
      } else {
        showError('修复脚本执行失败');
      }
    } finally {
      setExecuting(false);
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'windows':
        return 'bg-blue-100 text-blue-800';
      case 'linux':
        return 'bg-green-100 text-green-800';
      case 'docker':
        return 'bg-purple-100 text-purple-800';
      case 'k8s':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (record: RepairRecord) => {
    if (record.blocked) {
      return <XCircle className="h-4 w-4 text-red-500" />;
    }
    if (record.success) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
    return <AlertCircle className="h-4 w-4 text-orange-500" />;
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
          description="无法加载修复数据，请稍后重试"
          action={<Button onClick={() => { refetchScripts(); refetchHistory(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchScripts(); refetchHistory(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wrench className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">修复管理</h1>
            <p className="text-sm text-gray-500">执行和管理系统修复脚本</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchScripts(); refetchHistory(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowExecuteDialog(true)}>
            <Play className="h-4 w-4 mr-2" />
            执行修复
          </Button>
        </div>
      </div>

      {/* 修复脚本列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              可用修复脚本 ({scripts.length})
            </CardTitle>
            <Select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-48"
            >
              <option value="all">全部平台</option>
              {platforms.map((p) => (
                <option key={p} value={p}>{p.toUpperCase()}</option>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {filteredScripts.length === 0 ? (
            <EmptyState
              title="暂无修复脚本"
              description="当前没有可用的修复脚本"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredScripts.map((script) => (
                <Card key={`${script.platform}-${script.key}`} className="hover:shadow-md transition">
                  <CardContent className="pt-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge className={getPlatformColor(script.platform)}>
                          {script.platform.toUpperCase()}
                        </Badge>
                        <span className="text-xs text-gray-500">{script.key}</span>
                      </div>
                      <h3 className="font-medium text-gray-900">{script.name}</h3>
                      {script.description && (
                        <p className="text-sm text-gray-500">{script.description}</p>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full"
                        onClick={() => {
                          setSelectedPlatform(script.platform);
                          setSelectedScript(script.key);
                          setShowExecuteDialog(true);
                        }}
                      >
                        <Play className="h-4 w-4 mr-2" />
                        执行
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 修复历史记录 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            修复历史记录 ({history.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <LoadingSpinner />
          ) : history.length === 0 ? (
            <EmptyState
              title="暂无修复历史"
              description="当前没有修复执行记录"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>平台</TableHead>
                  <TableHead>脚本</TableHead>
                  <TableHead>主机</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((record) => (
                  <TableRow key={record.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="text-sm text-gray-500">
                      {new Date(record.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge className={getPlatformColor(record.platform)}>
                        {record.platform.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{record.script_name}</TableCell>
                    <TableCell>{record.host_name || '-'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(record)}
                        {record.blocked ? (
                          <Badge variant="destructive">已拦截</Badge>
                        ) : record.success ? (
                          <Badge variant="default">成功</Badge>
                        ) : (
                          <Badge variant="secondary">失败</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {record.duration_sec ? `${record.duration_sec.toFixed(2)}s` : '-'}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedRecord(record)}
                      >
                        查看详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 执行修复弹窗 */}
      <Dialog open={showExecuteDialog} onOpenChange={setShowExecuteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              执行修复脚本
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">平台</label>
              <Select
                value={selectedPlatform}
                onChange={(e) => setSelectedPlatform(e.target.value)}
              >
                <option value="all">选择平台</option>
                {platforms.map((p) => (
                  <option key={p} value={p}>{p.toUpperCase()}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">修复脚本</label>
              <Select
                value={selectedScript}
                onChange={(e) => setSelectedScript(e.target.value)}
                disabled={selectedPlatform === 'all'}
              >
                <option value="">选择脚本</option>
                {filteredScripts.map((s) => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">主机名（可选）</label>
              <Input
                value={hostName}
                onChange={(e) => setHostName(e.target.value)}
                placeholder="输入主机名"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">参数（可选）</label>
              <Input
                value={Object.entries(params).map(([k, v]) => `${k}=${v}`).join(', ')}
                onChange={(e) => {
                  const pairs = e.target.value.split(',').map(p => p.trim().split('='));
                  const newParams: Record<string, string> = {};
                  pairs.forEach(([k, v]) => {
                    if (k && v) newParams[k] = v;
                  });
                  setParams(newParams);
                }}
                placeholder="key1=value1, key2=value2"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowExecuteDialog(false)}>
              取消
            </Button>
            <Button onClick={handleExecute} disabled={executing || !selectedScript}>
              {executing ? '执行中...' : '执行'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 修复详情弹窗 */}
      {selectedRecord && (
        <Dialog open={!!selectedRecord} onOpenChange={() => setSelectedRecord(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>修复执行详情</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">平台</label>
                  <Badge className={getPlatformColor(selectedRecord.platform)}>
                    {selectedRecord.platform.toUpperCase()}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">脚本</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRecord.script_name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">主机</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRecord.host_name || '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">时间</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {new Date(selectedRecord.timestamp).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">状态</label>
                  <div className="flex items-center gap-2 mt-1">
                    {getStatusIcon(selectedRecord)}
                    {selectedRecord.blocked ? (
                      <Badge variant="destructive">已拦截</Badge>
                    ) : selectedRecord.success ? (
                      <Badge variant="default">成功</Badge>
                    ) : (
                      <Badge variant="secondary">失败</Badge>
                    )}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">耗时</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {selectedRecord.duration_sec ? `${selectedRecord.duration_sec.toFixed(2)}s` : '-'}
                  </p>
                </div>
              </div>
              {selectedRecord.output && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">输出</label>
                  <pre className="mt-1 p-3 bg-gray-100 rounded text-sm overflow-auto max-h-48">
                    {selectedRecord.output}
                  </pre>
                </div>
              )}
              {selectedRecord.error && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">错误</label>
                  <pre className="mt-1 p-3 bg-red-50 rounded text-sm overflow-auto max-h-48 text-red-800">
                    {selectedRecord.error}
                  </pre>
                </div>
              )}
              {selectedRecord.blocked && selectedRecord.safe_alternative && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">安全替代方案</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRecord.safe_alternative}</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedRecord(null)}>
                关闭
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}