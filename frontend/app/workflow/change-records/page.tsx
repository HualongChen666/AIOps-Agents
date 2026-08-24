'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ChangeRecord {
  id: string;
  changeId: string;
  changeTitle: string;
  type: 'routine' | 'emergency' | 'standard';
  status: 'completed' | 'rolled_back' | 'failed';
  requester: string;
  approver?: string;
  executor?: string;
  scheduledStart: string;
  scheduledEnd: string;
  actualStart?: string;
  actualEnd?: string;
  duration?: number;
  riskLevel: 'low' | 'medium' | 'high';
  impact?: string;
  rollbackExecuted: boolean;
  createdAt: string;
  completedAt?: string;
}

interface ChangeStats {
  totalChanges: number;
  completedChanges: number;
  rolledBackChanges: number;
  failedChanges: number;
  avgDuration: number;
  successRate: number;
}

export default function ChangeRecordsPage() {
  const [records, setRecords] = useState<ChangeRecord[]>([]);
  const [stats, setStats] = useState<ChangeStats>({
    totalChanges: 0,
    completedChanges: 0,
    rolledBackChanges: 0,
    failedChanges: 0,
    avgDuration: 0,
    successRate: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const loadRecords = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterType !== 'all') params.type = filterType;
      if (searchTerm) params.search = searchTerm;
      if (dateFrom) params.dateFrom = dateFrom;
      if (dateTo) params.dateTo = dateTo;

      const response = await api.get<{ records: ChangeRecord[]; stats: ChangeStats }>('/api/v1/change-records', { params });
      setRecords(response.data?.records || []);
      setStats(response.data?.stats || stats);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载变更记录失败');
      console.error('加载变更记录失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [filterStatus, filterType, searchTerm, dateFrom, dateTo]);

  const handleExport = async () => {
    try {
      const response = await api.get('/api/v1/change-records/export', {
        responseType: 'blob',
        params: {
          status: filterStatus !== 'all' ? filterStatus : undefined,
          type: filterType !== 'all' ? filterType : undefined,
          dateFrom,
          dateTo,
        },
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `change-records-${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      setError(err.response?.data?.message || '导出失败');
      console.error('导出失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      completed: 'default',
      rolled_back: 'destructive',
      failed: 'destructive',
    };
    const labels: Record<string, string> = {
      completed: '已完成',
      rolled_back: '已回滚',
      failed: '失败',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const getTypeBadge = (type: string) => {
    const variants: Record<string, any> = {
      routine: 'secondary',
      emergency: 'destructive',
      standard: 'default',
    };
    const labels: Record<string, string> = {
      routine: '常规',
      emergency: '紧急',
      standard: '标准',
    };
    return <Badge variant={variants[type] || 'outline'}>{labels[type] || type}</Badge>;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">变更记录</h1>
          <p className="text-gray-600 mt-1">查看和导出历史变更记录</p>
        </div>
        <Button onClick={handleExport}>导出记录</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总变更数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalChanges}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.completedChanges}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已回滚</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{stats.rolledBackChanges}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-orange-600">{stats.failedChanges}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">平均耗时</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.avgDuration}s</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.successRate}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Input
              placeholder="搜索变更标题..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="all">全部状态</option>
              <option value="completed">已完成</option>
              <option value="rolled_back">已回滚</option>
              <option value="failed">失败</option>
            </select>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="all">全部类型</option>
              <option value="routine">常规</option>
              <option value="standard">标准</option>
              <option value="emergency">紧急</option>
            </select>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              placeholder="开始日期"
            />
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              placeholder="结束日期"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>变更记录列表</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : records.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无变更记录</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>变更标题</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>请求人</TableHead>
                  <TableHead>执行人</TableHead>
                  <TableHead>计划时间</TableHead>
                  <TableHead>实际时间</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>回滚</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell className="font-mono text-sm">{record.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{record.changeTitle}</TableCell>
                    <TableCell>{getTypeBadge(record.type)}</TableCell>
                    <TableCell>{getStatusBadge(record.status)}</TableCell>
                    <TableCell>
                      <Badge variant={record.riskLevel === 'high' ? 'destructive' : 'outline'}>
                        {record.riskLevel === 'low' ? '低' : record.riskLevel === 'medium' ? '中' : '高'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-600">{record.requester}</TableCell>
                    <TableCell className="text-gray-600">{record.executor || '-'}</TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(record.scheduledStart).toLocaleString('zh-CN')}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {record.actualStart ? new Date(record.actualStart).toLocaleString('zh-CN') : '-'}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {record.duration ? `${record.duration}s` : '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={record.rollbackExecuted ? 'destructive' : 'secondary'}>
                        {record.rollbackExecuted ? '是' : '否'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
