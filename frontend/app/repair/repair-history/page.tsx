'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface RepairHistory {
  id: string;
  repairType: string;
  targetResource: string;
  issueDescription: string;
  status: 'success' | 'failed' | 'partial' | 'cancelled';
  startTime: string;
  endTime?: string;
  duration?: number;
  executedBy: string;
  details?: string;
}

export default function RepairHistoryPage() {
  const [history, setHistory] = useState<RepairHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      const resp = await api.get('/api/v1/repair/history', { params });
      const items = resp.data?.items || [];
      setHistory(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          repairType: item.repair_type || item.type || '未知类型',
          targetResource: item.target_resource || item.resource || '',
          issueDescription: item.issue_description || item.description || '',
          status: (item.status || 'success') as RepairHistory['status'],
          startTime: item.start_time || item.timestamp || new Date().toISOString(),
          endTime: item.end_time,
          duration: item.duration,
          executedBy: item.executed_by || item.executor || 'System',
          details: item.details,
        }))
      );
    } catch (err: any) {
      console.error('加载修复历史失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [dateFrom, dateTo]);

  const handleExport = async () => {
    try {
      const resp = await api.get('/api/v1/repair/history/export', {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `repair-history-${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      console.error('导出失败:', err);
      setError(err.message || '导出失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'partial':
        return 'bg-yellow-100 text-yellow-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredHistory = history.filter((item) => {
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus;
    const matchesSearch = item.repairType.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.targetResource.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.issueDescription.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">修复历史</h1>
        <div className="flex gap-2">
          <Button onClick={loadHistory} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </Button>
          <Button onClick={handleExport} variant="outline">
            导出
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{history.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">成功</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{history.filter(h => h.status === 'success').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{history.filter(h => h.status === 'failed').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {history.length > 0 ? ((history.filter(h => h.status === 'success').length / history.length) * 100).toFixed(1) : 0}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选和搜索 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap">
            <Input
              placeholder="搜索修复类型、资源或描述..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-md"
            />
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="max-w-[180px]"
            />
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="max-w-[180px]"
            />
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="状态筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="success">成功</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
                <SelectItem value="partial">部分成功</SelectItem>
                <SelectItem value="cancelled">已取消</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 历史记录列表 */}
      <Card>
        <CardHeader>
          <CardTitle>修复历史记录</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredHistory.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>修复类型</TableHead>
                  <TableHead>目标资源</TableHead>
                  <TableHead>问题描述</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>结束时间</TableHead>
                  <TableHead>持续时间</TableHead>
                  <TableHead>执行者</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredHistory.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-sm">{item.id}</TableCell>
                    <TableCell className="font-medium">{item.repairType}</TableCell>
                    <TableCell className="font-mono text-sm">{item.targetResource}</TableCell>
                    <TableCell className="max-w-xs truncate">{item.issueDescription}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(item.status)}>
                        {item.status === 'success' ? '成功' :
                         item.status === 'failed' ? '失败' :
                         item.status === 'partial' ? '部分成功' : '已取消'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(item.startTime).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {item.endTime ? new Date(item.endTime).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {item.duration ? `${item.duration}s` : '-'}
                    </TableCell>
                    <TableCell>{item.executedBy}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm">
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
    </div>
  );
}
