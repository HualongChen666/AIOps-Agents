'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface CrossPlatformRepair {
  id: string;
  name: string;
  description: string;
  platforms: Array<'linux' | 'windows' | 'macos' | 'docker' | 'kubernetes'>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startTime: string;
  endTime?: string;
  targetCount: number;
  completedCount: number;
}

export default function CrossPlatformPage() {
  const [repairs, setRepairs] = useState<CrossPlatformRepair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterPlatform, setFilterPlatform] = useState<string>('all');

  const loadRepairs = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/cross-platform');
      const items = resp.data?.items || [];
      setRepairs(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          name: item.name || '',
          description: item.description || '',
          platforms: (item.platforms || []) as CrossPlatformRepair['platforms'],
          status: (item.status || 'pending') as CrossPlatformRepair['status'],
          progress: item.progress || 0,
          startTime: item.start_time || new Date().toISOString(),
          endTime: item.end_time,
          targetCount: item.target_count || 0,
          completedCount: item.completed_count || 0,
        }))
      );
    } catch (err: any) {
      console.error('加载跨平台修复失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepairs();
  }, []);

  const handleExecuteRepair = async (repairId: string) => {
    try {
      await api.post(`/api/v1/repair/cross-platform/${repairId}/execute`);
      await loadRepairs();
    } catch (err: any) {
      console.error('执行修复失败:', err);
      setError(err.message || '执行失败');
    }
  };

  const handleCancelRepair = async (repairId: string) => {
    try {
      await api.post(`/api/v1/repair/cross-platform/${repairId}/cancel`);
      await loadRepairs();
    } catch (err: any) {
      console.error('取消修复失败:', err);
      setError(err.message || '取消失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'linux':
        return 'bg-green-100 text-green-800';
      case 'windows':
        return 'bg-blue-100 text-blue-800';
      case 'macos':
        return 'bg-purple-100 text-purple-800';
      case 'docker':
        return 'bg-cyan-100 text-cyan-800';
      case 'kubernetes':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredRepairs = repairs.filter((repair) => {
    if (filterPlatform === 'all') return true;
    return repair.platforms.includes(filterPlatform as any);
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">跨平台修复</h1>
        <div className="flex gap-2">
          <Button onClick={loadRepairs} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 平台筛选 */}
      <Card>
        <CardContent className="pt-6">
          <Select value={filterPlatform} onValueChange={setFilterPlatform}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="筛选平台" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部平台</SelectItem>
              <SelectItem value="linux">Linux</SelectItem>
              <SelectItem value="windows">Windows</SelectItem>
              <SelectItem value="macos">macOS</SelectItem>
              <SelectItem value="docker">Docker</SelectItem>
              <SelectItem value="kubernetes">Kubernetes</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* 修复列表 */}
      <Card>
        <CardHeader>
          <CardTitle>跨平台修复任务</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredRepairs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>支持平台</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>进度</TableHead>
                  <TableHead>目标/完成</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRepairs.map((repair) => (
                  <TableRow key={repair.id}>
                    <TableCell className="font-mono text-sm">{repair.id}</TableCell>
                    <TableCell className="font-medium">{repair.name}</TableCell>
                    <TableCell className="max-w-xs truncate">{repair.description}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {repair.platforms.map((platform) => (
                          <Badge key={platform} className={getPlatformColor(platform)}>
                            {platform}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(repair.status)}>
                        {repair.status === 'pending' ? '待执行' :
                         repair.status === 'running' ? '运行中' :
                         repair.status === 'completed' ? '已完成' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${repair.progress}%` }}
                          />
                        </div>
                        <span className="text-sm">{repair.progress}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">{repair.completedCount}/{repair.targetCount}</span>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(repair.startTime).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {repair.status === 'pending' && (
                          <Button
                            size="sm"
                            onClick={() => handleExecuteRepair(repair.id)}
                          >
                            执行
                          </Button>
                        )}
                        {repair.status === 'running' && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleCancelRepair(repair.id)}
                          >
                            取消
                          </Button>
                        )}
                        {repair.status === 'completed' && (
                          <Button variant="ghost" size="sm">
                            查看详情
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
